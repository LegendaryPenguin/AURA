# `<TASK_ID>`: `<Task Name>`

| Field | Value |
| ----- | ----- |
| **Status** | `Todo` |
| **Maturity** | `Planned` |
| **Owner** | _Unassigned_ |
| **Phase** | `<Phase>` |
| **Stream** | `<WS# — Name>` |

---

## Scope — Owned Files

- `<path>`
- `<path>`

> **Collision rule:** Modify only listed files unless scope is formally updated.

---

## Dependencies

- Upstream tasks: `<TASK_ID>`, `<TASK_ID>`
- Downstream tasks: `<TASK_ID>`, `<TASK_ID>`
- Runtime dependencies (routes/pipelines/config): `<details>`
- Contract dependencies (schemas/interfaces): `<details>`

---

## Work

- `<deliverable>`
- `<deliverable>`

---

## Verification

- [ ] `<automated verification>`
- [ ] `<integration verification>`
- [ ] `<manual verification>`

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: <TASK_ID>
  MaturityBefore: <level>
  MaturityAfter: <level>
  ChangeSummary: <what changed>
  GatesRun:
    - <test/check>
  EvidenceLinks:
    - <path/log/artifact>
  DependenciesClosed: <yes/no + note>
  ResidualRisk: <risk + owner>
  RollbackRequired: <Yes/No>
  Signoff:
    - <workstream/owner>
```

---

## Rollback

- Trigger conditions: `<what forces rollback>`
- Rollback target maturity: `<level>`
- Blocker owner: `<owner>`
- Re-promotion criteria: `<criteria>`

---

## Residual Risks

- `<risk>` — Owner: `<owner>` — Mitigation: `<mitigation>`
