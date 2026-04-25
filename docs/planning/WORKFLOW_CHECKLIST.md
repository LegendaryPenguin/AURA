# Task Workflow Checklist

Use this at the start and end of every task to keep status, scope, testing, and commits consistent.

---

## Start of Task Prompt

I am claiming `<TASK_ID>`.

1. Read `docs/planning/MASTER_ROADMAP.md` and `docs/planning/tasks/<TASK_ID>.md`.
2. If needed, set task Status to `In-Progress` and Owner to `Farrell` in both the task file and roadmap.
3. Summarize scope, owned files, constraints, and dependency rules from `.cursorrules`.
4. Produce an execution plan with checkpoints, risk notes, and a test plan.
5. Do not modify files outside the task's owned file list.

### Start Gate Checklist

- Task file read
- Roadmap read
- Status/Owner synced in both places
- Scope + owned files confirmed
- Plan created with verification steps

---

## End of Task Prompt

I've finished `<TASK_ID>`.

1. Re-read `docs/planning/tasks/<TASK_ID>.md` and `docs/planning/MASTER_ROADMAP.md`.
2. Run required verification first:
  - Contract tests: `pytest tests/contract/ -v`
  - Workstream-specific tests (WS2: relevant client/unit tests)
3. If tests pass, set Status to `Done` in both places.
4. Move any `Remaining` items to `Completed` (or explain blockers).
5. Commit only relevant files with message: `<TASK_ID>: <short outcome>`.
6. If tests fail, do not mark `Done`; report failures and next fixes.
7. Return a concise completion report: changed files, tests run/results, residual risks, and follow-ups.

### End Gate Checklist

- Contract tests run
- WS-specific tests run
- If tests pass: task + roadmap status = Done
- If tests fail: status remains In-Progress with blockers noted
- Remaining items reconciled
- Focused commit created
- Completion report received

---

## Notes

- Prefer idempotent updates (skip no-op edits when already synced).
- Never edit files outside owned scope unless task scope is formally updated.
- Keep commit message style consistent for easy tracking.