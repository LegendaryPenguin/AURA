# Task Command Automation

This document defines the command-driven workflow for checklist execution.

## Commands

- Start task flow:
  - `/starttask @WS3-B`
  - CLI equivalent: `./starttask WS3-B`
- End task flow:
  - `/endtask @WS3-B`
  - CLI equivalent: `./endtask WS3-B`

If slash commands are used in chat, the hook router returns the exact terminal command to run.

Both commands are consolidated two-step flows:

- `starttask`: dry-run preflight -> strict validation
- `endtask`: dry-run preflight -> strict execution (tests + promotion decision path)

## Execution Policy

- Every consolidated command executes dry-run first, then strict mode.
- Out of scope: scaffold/code generation.

## Core Runner

- Runner script: `scripts/planning/task_cycle.sh`
- Modes:
  - `start <TASK_ID> [--target <Maturity>] [--dry-run] [--strict]`
  - `end <TASK_ID> [--dry-run] [--strict]`

## Artifacts

Reports are generated under:

- `docs/planning/evidence/start/<TASK_ID>/<timestamp>/`
- `docs/planning/evidence/end/<TASK_ID>/<timestamp>/`

Each run writes:

- Markdown summary report
- JSON machine-readable report
- End mode additionally writes `run_tests.log` when not in dry-run.

## Safety Rules

- No automatic code scaffold generation.
- No cross-scope edits.
- Missing required task sections result in `DoNotPromote`.
- `--strict` enforces governance/roadmap field checks and fails fast when unsynchronized.
