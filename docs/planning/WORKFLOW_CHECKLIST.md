# Task Workflow Checklist

This is the day-to-day operating gate for roadmap alignment.
If any required gate field is missing, outcome is `DoNotPromote`.

---

## Start of Task Prompt

I am claiming `<TASK_ID>`.

1. Read `docs/planning/MASTER_ROADMAP.md` and `docs/planning/tasks/<TASK_ID>.md`.
2. Confirm task file contains required sections: `Maturity`, `Dependencies`, `Promotion Evidence`, `Rollback`, `Residual Risks`.
3. Set `MaturityBefore` and declare target maturity transition for this task pass.
4. If needed, set task `Status` to `In-Progress` and Owner in both task file and roadmap.
5. Summarize scope, owned files, constraints, and dependency rules from `.cursorrules`.
6. Produce an execution plan with checkpoints, risk notes, and a test plan.
7. Do not modify files outside the task's owned file list.

### Start Gate Checklist

- Task file read
- Roadmap read
- Task template compliance confirmed
- `MaturityBefore` recorded
- Target maturity declared
- Status/Owner synced in both places
- Scope + owned files confirmed
- Plan created with verification steps

---

## End of Task Prompt

I've finished `<TASK_ID>`.

1. Re-read `docs/planning/tasks/<TASK_ID>.md` and `docs/planning/MASTER_ROADMAP.md`.
2. Run required verification:
  - Contract tests: `pytest tests/contract/ -v`
  - Workstream-specific tests (WS2: relevant client/unit tests)
3. Validate dependency closure for the target maturity level.
4. Prepare required completion report fields:
   - `MaturityBefore`
   - `MaturityAfter`
   - `DependenciesClosed`
   - `EvidenceLinks`
   - `ResidualRisk`
   - `RollbackRequired` (`Yes`/`No`)
5. Promotion decision:
   - If any required field is missing -> `DoNotPromote`
   - If required gates fail -> `DoNotPromote`
   - If promoted gate regressed -> apply rollback and assign blocker owner
6. If promotion is valid, update task/roadmap status and maturity accordingly.
7. Move any `Remaining` items to `Completed` (or explain blockers).
8. Commit only relevant files with message: `<TASK_ID>: <short outcome>`.
9. Return a concise completion report with the required fields above.

### End Gate Checklist

- Contract tests run
- WS-specific tests run
- Dependency closure validated
- Required completion fields present
- Promotion outcome recorded (`Promote` or `DoNotPromote`)
- If promoted gate regressed: rollback applied and blocker owner assigned
- If promoted: task + roadmap maturity/status synced
- If not promoted: status remains In-Progress with blockers noted
- Remaining items reconciled
- Focused commit created
- Completion report received

---

## Notes

- Prefer idempotent updates (skip no-op edits when already synced).
- Never edit files outside owned scope unless task scope is formally updated.
- Keep commit message style consistent for easy tracking.
- Checklist logic references roadmap governance. Do not create alternate promotion rules in task files.