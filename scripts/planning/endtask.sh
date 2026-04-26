#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="${ROOT_DIR}/scripts/planning/task_cycle.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <TASK_ID>" >&2
  exit 1
fi

TASK_ID="$1"
shift

if [[ $# -gt 0 ]]; then
  echo "Consolidated endtask takes only TASK_ID (no extra flags)." >&2
  exit 1
fi

echo "[endtask] Step 1/2: dry-run preflight"
set +e
DRY_OUTPUT="$("$RUNNER" end "$TASK_ID" --dry-run 2>&1)"
DRY_RC=$?
set -e
printf '%s\n' "$DRY_OUTPUT"

echo "[endtask] Step 2/2: strict execution"
set +e
STRICT_OUTPUT="$("$RUNNER" end "$TASK_ID" --strict 2>&1)"
STRICT_RC=$?
set -e
printf '%s\n' "$STRICT_OUTPUT"

STRICT_REPORT_PATH="$(python3 - <<'PY' "$STRICT_OUTPUT"
import re
import sys

text = sys.argv[1]
match = re.search(r"See\s+(\S+/end-report\.md)", text)
print(match.group(1) if match else "")
PY
)"

STRICT_REPORT_JSON=""
if [[ -n "$STRICT_REPORT_PATH" ]]; then
  STRICT_REPORT_JSON="${STRICT_REPORT_PATH%.md}.json"
fi

SUMMARY="$(python3 - <<'PY' "$STRICT_REPORT_JSON" "$STRICT_RC"
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1]) if sys.argv[1] else None
strict_rc = int(sys.argv[2])

if not report_path or not report_path.exists():
    print("ENDTASK RESULT: UNKNOWN")
    print("- Could not locate strict end-report artifact.")
    print("- Re-run: ./endtask <TASK_ID>")
    raise SystemExit(0)

data = json.loads(report_path.read_text(encoding="utf-8"))
task = data.get("task", {})
missing_sections = task.get("missing_sections", [])
promotion = data.get("promotion_outcome", "Unknown")
checklist = data.get("checklist_status", "Unknown")

if strict_rc == 0 and promotion == "Promote":
    print("ENDTASK RESULT: PASS (ready to close)")
else:
    print("ENDTASK RESULT: ACTION REQUIRED (not ready to close)")

print(f"- Promotion outcome: {promotion}")
print(f"- Checklist status: {checklist}")
print(f"- Task file: {task.get('task_file', 'Unknown')}")

if missing_sections:
    print("- Remaining required sections to add:")
    for section in missing_sections:
        print(f"  - {section}")
else:
    print("- Required task sections: complete")

print(f"- Full report: {report_path.with_suffix('.md')}")
if report_path.with_name("run_tests.log").exists():
    print(f"- Test log: {report_path.with_name('run_tests.log')}")
else:
    print("- Test log: not generated (or tests did not run)")
PY
)"

echo
echo "=== Endtask Quick Summary ==="
printf '%s\n' "$SUMMARY"

if [[ "$STRICT_RC" -ne 0 ]]; then
  exit "$STRICT_RC"
fi
