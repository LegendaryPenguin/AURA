#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="${ROOT_DIR}/scripts/planning/task_cycle.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <TASK_ID> [--target <Maturity>]" >&2
  exit 1
fi

TASK_ID="$1"
shift

EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      EXTRA_ARGS+=("$1" "${2:-}")
      shift 2
      ;;
    *)
      echo "Unknown option for consolidated starttask: $1" >&2
      echo "Allowed options: --target <Maturity>" >&2
      exit 1
      ;;
  esac
done

echo "[starttask] Step 1/2: dry-run preflight"
set +e
DRY_OUTPUT="$("$RUNNER" start "$TASK_ID" --dry-run "${EXTRA_ARGS[@]}" 2>&1)"
DRY_RC=$?
set -e
printf '%s\n' "$DRY_OUTPUT"

echo "[starttask] Step 2/2: strict validation"
set +e
STRICT_OUTPUT="$("$RUNNER" start "$TASK_ID" --strict "${EXTRA_ARGS[@]}" 2>&1)"
STRICT_RC=$?
set -e
printf '%s\n' "$STRICT_OUTPUT"

STRICT_REPORT_PATH="$(python3 - <<'PY' "$STRICT_OUTPUT"
import re
import sys

text = sys.argv[1]
match = re.search(r"Artifact:\s+(\S+/start-report\.md)", text)
if not match:
    match = re.search(r"See\s+(\S+/start-report\.md)", text)
print(match.group(1) if match else "")
PY
)"

STRICT_REPORT_JSON=""
if [[ -n "$STRICT_REPORT_PATH" ]]; then
  STRICT_REPORT_JSON="${STRICT_REPORT_PATH%.md}.json"
fi

SUMMARY="$(python3 - <<'PY' "$STRICT_REPORT_JSON" "$STRICT_RC" "$DRY_RC"
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1]) if sys.argv[1] else None
strict_rc = int(sys.argv[2])
dry_rc = int(sys.argv[3])

if not report_path or not report_path.exists():
    print("STARTTASK RESULT: UNKNOWN")
    print("- Could not locate strict start-report artifact.")
    print("- Re-run: ./starttask <TASK_ID>")
    raise SystemExit(0)

task = json.loads(report_path.read_text(encoding="utf-8"))
missing_sections = task.get("missing_sections", [])

if strict_rc == 0:
    print("STARTTASK RESULT: PASS (ready to start)")
else:
    print("STARTTASK RESULT: ACTION REQUIRED (not ready to start)")

print(f"- Task file: {task.get('task_file', 'Unknown')}")
print(f"- Current status: {task.get('status') or 'Unknown'}")
print(f"- Current maturity: {task.get('maturity') or 'Unknown'}")

if missing_sections:
    print("- Missing required sections to complete before start:")
    for section in missing_sections:
        print(f"  - {section}")
else:
    print("- Required task sections: complete")

if dry_rc != 0:
    print("- Dry-run preflight had failures; review strict report details.")
print(f"- Full report: {report_path.with_suffix('.md')}")
PY
)"

echo
echo "=== Starttask Quick Summary ==="
printf '%s\n' "$SUMMARY"

if [[ "$STRICT_RC" -ne 0 ]]; then
  exit "$STRICT_RC"
fi
