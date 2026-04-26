#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="${ROOT_DIR}/docs/planning/evidence"
TASKS_DIR="${ROOT_DIR}/docs/planning/tasks"
CHECKLIST_FILE="${ROOT_DIR}/docs/planning/WORKFLOW_CHECKLIST.md"
ROADMAP_FILE="${ROOT_DIR}/docs/planning/MASTER_ROADMAP.md"
TEMPLATE_FILE="${ROOT_DIR}/docs/planning/TASK_TEMPLATE.md"
GOVERNANCE_FILE="${ROOT_DIR}/docs/planning/GLOBAL_ALIGNMENT_GOVERNANCE.md"
RULES_FILE="${ROOT_DIR}/.cursorrules"
RUN_TESTS_SCRIPT="${ROOT_DIR}/scripts/dev/run_tests.sh"

usage() {
  echo "Usage:"
  echo "  $0 start <TASK_ID> [--target <Maturity>] [--dry-run] [--strict]"
  echo "  $0 end <TASK_ID> [--dry-run] [--strict]"
}

normalize_task_id() {
  local raw="$1"
  raw="${raw#@}"
  echo "${raw^^}"
}

timestamp_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    return 1
  fi
}

resolve_task_file() {
  local task_id="$1"
  local pattern="${TASKS_DIR}/${task_id}-"*.md
  local matches=()
  shopt -s nullglob
  matches=($pattern)
  shopt -u nullglob

  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "Task file not found for ${task_id}. Expected pattern: docs/planning/tasks/${task_id}-*.md" >&2
    return 1
  fi
  if [[ ${#matches[@]} -gt 1 ]]; then
    echo "Multiple task files found for ${task_id}. Resolve ambiguity manually." >&2
    printf '%s\n' "${matches[@]}" >&2
    return 1
  fi
  echo "${matches[0]}"
}

json_escape_python='import json,sys; print(json.dumps(sys.stdin.read()))'

parse_task_report_json() {
  local task_id="$1"
  local task_file="$2"
  python3 - <<'PY' "$task_id" "$task_file"
import json
import re
import sys
from pathlib import Path

task_id = sys.argv[1]
task_file = Path(sys.argv[2])
text = task_file.read_text(encoding="utf-8")

required_sections = [
    "Scope — Owned Files",
    "Dependencies",
    "Verification",
    "Promotion Evidence",
    "Rollback",
    "Residual Risks",
]

missing_sections = []
for section in required_sections:
    if f"## {section}" not in text:
        missing_sections.append(section)

def table_field(name: str):
    m = re.search(rf"\|\s*\*\*{re.escape(name)}\*\*\s*\|\s*`?([^|`]+)`?\s*\|", text)
    return m.group(1).strip() if m else None

status = table_field("Status")
maturity = table_field("Maturity")
owner = table_field("Owner")
phase = table_field("Phase")
stream = table_field("Stream")

upstream = re.search(r"-\s*Upstream tasks:\s*(.+)", text)
downstream = re.search(r"-\s*Downstream tasks:\s*(.+)", text)

report = {
    "task_id": task_id,
    "task_file": str(task_file),
    "status": status,
    "maturity": maturity,
    "owner": owner,
    "phase": phase,
    "stream": stream,
    "missing_sections": missing_sections,
    "upstream_tasks": upstream.group(1).strip() if upstream else "",
    "downstream_tasks": downstream.group(1).strip() if downstream else "",
}

print(json.dumps(report))
PY
}

check_governance_strict() {
  local errors=0
  if [[ ! -f "$GOVERNANCE_FILE" ]]; then
    echo "Strict check failed: missing governance file ${GOVERNANCE_FILE}." >&2
    return 1
  fi
  if ! python3 - <<'PY' "$GOVERNANCE_FILE"
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
raise SystemExit(0 if "PromotionOutcome" in text else 1)
PY
  then
    echo "Strict check failed: Governance file missing PromotionOutcome." >&2
    errors=1
  fi
  if ! python3 - <<'PY' "$GOVERNANCE_FILE"
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
raise SystemExit(0 if "EvidenceEnvironment" in text else 1)
PY
  then
    echo "Strict check failed: Governance file missing EvidenceEnvironment." >&2
    errors=1
  fi
  if ! python3 - <<'PY' "$GOVERNANCE_FILE"
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
raise SystemExit(0 if "HardwareProfile" in text else 1)
PY
  then
    echo "Strict check failed: Governance file missing HardwareProfile." >&2
    errors=1
  fi
  if ! python3 - <<'PY' "$ROADMAP_FILE"
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
raise SystemExit(0 if "Phase Closure Matrix" in text else 1)
PY
  then
    echo "Strict check failed: Roadmap missing Phase Closure Matrix." >&2
    errors=1
  fi
  return "$errors"
}

write_markdown_artifact() {
  local output_file="$1"
  local title="$2"
  local task_id="$3"
  local mode="$4"
  local dry_run="$5"
  local strict="$6"
  local target="${7:-}"
  local promotion_outcome="${8:-N/A}"
  local check_status="${9:-N/A}"
  local task_json="${10}"
  local commands_json="${11:-[]}"
  local strict_result="${12:-not-run}"

  local now
  now="$(date -u +"%Y-%m-%d %H:%M:%SZ")"

  python3 - <<'PY' "$output_file" "$title" "$task_id" "$mode" "$dry_run" "$strict" "$target" "$promotion_outcome" "$check_status" "$task_json" "$commands_json" "$strict_result" "$now"
import json
import sys
from pathlib import Path

(
    output_file,
    title,
    task_id,
    mode,
    dry_run,
    strict,
    target,
    promotion_outcome,
    check_status,
    task_json,
    commands_json,
    strict_result,
    now,
) = sys.argv[1:]

task = json.loads(task_json)
commands = json.loads(commands_json)

lines = [
    f"# {title}",
    "",
    f"- Task: `{task_id}`",
    f"- Mode: `{mode}`",
    f"- DryRun: `{dry_run}`",
    f"- Strict: `{strict}`",
    f"- GeneratedAtUTC: `{now}`",
    f"- TaskFile: `{task.get('task_file', '')}`",
    f"- CurrentStatus: `{task.get('status') or 'Unknown'}`",
    f"- CurrentMaturity: `{task.get('maturity') or 'Unknown'}`",
    f"- Owner: `{task.get('owner') or 'Unknown'}`",
    f"- TargetMaturity: `{target or 'N/A'}`",
    f"- ChecklistStatus: `{check_status}`",
    f"- StrictChecks: `{strict_result}`",
    f"- PromotionOutcome: `{promotion_outcome}`",
    "",
    "## Missing Required Sections",
]

missing = task.get("missing_sections", [])
if missing:
    for item in missing:
        lines.append(f"- {item}")
else:
    lines.append("- None")

lines.extend([
    "",
    "## Dependencies",
    f"- Upstream: {task.get('upstream_tasks') or 'N/A'}",
    f"- Downstream: {task.get('downstream_tasks') or 'N/A'}",
    "",
    "## Planned/Executed Commands",
])

if commands:
    for cmd in commands:
        lines.append(f"- `{cmd}`")
else:
    lines.append("- None")

Path(output_file).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

run_and_capture() {
  local cmd="$1"
  local log_file="$2"
  set +e
  bash -lc "$cmd" >"$log_file" 2>&1
  local rc=$?
  set -e
  return $rc
}

main() {
  if [[ $# -lt 2 ]]; then
    usage
    exit 1
  fi

  local mode="$1"
  shift
  local task_id
  task_id="$(normalize_task_id "$1")"
  shift

  local target_maturity=""
  local dry_run="false"
  local strict="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)
        target_maturity="${2:-}"
        shift 2
        ;;
      --dry-run)
        dry_run="true"
        shift
        ;;
      --strict)
        strict="true"
        shift
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
  done

  if [[ ! "$task_id" =~ ^WS[1-4]-[A-Z]$ ]]; then
    echo "Invalid TASK_ID '${task_id}'. Expected format like WS3-B." >&2
    exit 1
  fi

  require_file "$CHECKLIST_FILE"
  require_file "$ROADMAP_FILE"
  require_file "$RULES_FILE"
  require_file "$RUN_TESTS_SCRIPT"

  local optional_warnings=()
  if [[ ! -f "$TEMPLATE_FILE" ]]; then
    optional_warnings+=("Missing optional file: ${TEMPLATE_FILE}")
  fi
  if [[ ! -f "$GOVERNANCE_FILE" ]]; then
    optional_warnings+=("Missing optional file: ${GOVERNANCE_FILE}")
  fi

  local task_file
  task_file="$(resolve_task_file "$task_id")"

  local task_json
  task_json="$(parse_task_report_json "$task_id" "$task_file")"

  local ts
  ts="$(timestamp_utc)"
  local out_dir
  out_dir="${EVIDENCE_DIR}/${mode}/${task_id}/${ts}"
  mkdir -p "$out_dir"

  local strict_result="not-run"
  if [[ "$strict" == "true" ]]; then
    if check_governance_strict; then
      strict_result="pass"
    else
      strict_result="fail"
    fi
  fi

  local missing_count
  missing_count="$(python3 - <<'PY' "$task_json"
import json,sys
print(len(json.loads(sys.argv[1]).get("missing_sections", [])))
PY
)"

  if [[ "$mode" == "start" ]]; then
    local checklist_status="pass"
    if [[ "$missing_count" != "0" ]]; then
      checklist_status="fail"
    fi
    if [[ ${#optional_warnings[@]} -gt 0 ]]; then
      checklist_status="warn"
    fi
    if [[ "$strict_result" == "fail" ]]; then
      checklist_status="fail"
    fi

    local start_commands_json='[]'
    write_markdown_artifact \
      "${out_dir}/start-report.md" \
      "Start Task Report" \
      "$task_id" \
      "$mode" \
      "$dry_run" \
      "$strict" \
      "$target_maturity" \
      "N/A" \
      "$checklist_status" \
      "$task_json" \
      "$start_commands_json" \
      "$strict_result"

    printf '%s\n' "$task_json" > "${out_dir}/start-report.json"
    if [[ ${#optional_warnings[@]} -gt 0 ]]; then
      printf '%s\n' "${optional_warnings[@]}" > "${out_dir}/warnings.log"
    fi

    if [[ "$checklist_status" == "fail" ]]; then
      echo "Start flow completed with failures. See ${out_dir}/start-report.md"
      exit 2
    fi
    echo "Start flow completed. Artifact: ${out_dir}/start-report.md"
    exit 0
  fi

  if [[ "$mode" != "end" ]]; then
    echo "Unknown mode: $mode" >&2
    usage
    exit 1
  fi

  local commands=("${RUN_TESTS_SCRIPT}")
  local commands_json
  commands_json="$(printf '%s\n' "${commands[@]}" | python3 - <<'PY'
import json
import sys
print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))
PY
)"

  local checklist_status="pass"
  local promotion_outcome="Promote"

  if [[ "$missing_count" != "0" ]]; then
    checklist_status="fail"
    promotion_outcome="DoNotPromote"
  fi
  if [[ ${#optional_warnings[@]} -gt 0 && "$checklist_status" != "fail" ]]; then
    checklist_status="warn"
  fi
  if [[ "$strict_result" == "fail" ]]; then
    checklist_status="fail"
    promotion_outcome="DoNotPromote"
  fi

  if [[ "$dry_run" == "false" ]]; then
    local test_log="${out_dir}/run_tests.log"
    if ! run_and_capture "${RUN_TESTS_SCRIPT}" "$test_log"; then
      checklist_status="fail"
      promotion_outcome="DoNotPromote"
    fi
  else
    promotion_outcome="DoNotPromote"
  fi

  write_markdown_artifact \
    "${out_dir}/end-report.md" \
    "End Task Report" \
    "$task_id" \
    "$mode" \
    "$dry_run" \
    "$strict" \
    "$target_maturity" \
    "$promotion_outcome" \
    "$checklist_status" \
    "$task_json" \
    "$commands_json" \
    "$strict_result"

  python3 - <<'PY' "$task_json" "${out_dir}/end-report.json" "$promotion_outcome" "$checklist_status" "$dry_run" "$strict"
import json
import sys
from pathlib import Path

task = json.loads(sys.argv[1])
out = Path(sys.argv[2])
payload = {
    "task": task,
    "promotion_outcome": sys.argv[3],
    "checklist_status": sys.argv[4],
    "dry_run": sys.argv[5],
    "strict": sys.argv[6],
}
out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  if [[ ${#optional_warnings[@]} -gt 0 ]]; then
    printf '%s\n' "${optional_warnings[@]}" > "${out_dir}/warnings.log"
  fi

  if [[ "$promotion_outcome" == "DoNotPromote" ]]; then
    echo "End flow completed with DoNotPromote. See ${out_dir}/end-report.md"
    exit 2
  fi
  echo "End flow completed with Promote. See ${out_dir}/end-report.md"
}

main "$@"
