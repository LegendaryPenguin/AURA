# ARCHIVED — Roadmap Truth Alignment (Temporary Snapshot)

This archived temporary snapshot captured a transition state while canonical docs were being updated.

## Archive Notice

- This file is **non-authoritative** and retained for historical context only.
- Do not use this file for current promotion, phase, or maturity decisions.
- Use canonical planning docs:
  - `docs/planning/MASTER_ROADMAP.md`
  - `docs/planning/GLOBAL_ALIGNMENT_GOVERNANCE.md`
  - `docs/planning/WORKFLOW_CHECKLIST.md`

## Purpose

- Keep roadmap/task/checklist/gov changes synchronized during transition.
- Prevent phase overclaim by requiring explicit promotion evidence.
- Support deterministic task execution via `/starttask` and `/endtask` command flow.

## Temporary Operating Rules

- Roadmap phase claims must not exceed required task maturity.
- Missing required completion fields yields `DoNotPromote`.
- Evidence provenance is required for promotion-safe claims:
  - `PromotionOutcome`
  - `EvidenceEnvironment`
  - `HardwareProfile`
- Until canonical docs are fully synchronized, strict mode may intentionally fail to prevent overclaim.

## Command Automation Link

- Start flow:
  - `./scripts/planning/starttask.sh WSx-Y --dry-run`
- End flow:
  - `./scripts/planning/endtask.sh WSx-Y --dry-run`

Artifacts are written under `docs/planning/evidence/`.

## Exit Criteria for Temporary Status

This file can be retired when the following docs are aligned and enforced:

- `docs/planning/GLOBAL_ALIGNMENT_GOVERNANCE.md`
- `docs/planning/TASK_TEMPLATE.md`
- `docs/planning/WORKFLOW_CHECKLIST.md`
- `docs/planning/MASTER_ROADMAP.md`

Until then, treat this file as a transitional control note only.
