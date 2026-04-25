# WS1-C: Config Files & Environment

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Done`                     |
| **Maturity** | `Implemented`            |
| **Owner**   | Farrell                    |
| **Sprint**  | Sprint 0 (Foundation)      |
| **Stream**  | WS1 — Foundation & Contracts |

---

## Scope — Owned Files

- `config/models.yaml`
- `config/pipeline.yaml`
- `config/server.yaml`
- `config/demo.yaml`
- `.env.example`
- `.gitignore`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- Define all config YAML files with every tunable parameter documented in comments
- `.env.example` documents every environment variable with placeholder values
- `.gitignore` covers Python venvs, node_modules, model weights, certs, `__pycache__`, .env

---

## Verification

- [x] YAML files parse without error (validate with `pyyaml`)
- [x] `config_loader.py` (WS1-E) successfully loads and validates each file
- [x] All referenced file paths in config have clear documentation on expected contents

`config_loader.py` verification completed via WS1-E; all WS1-C checks are satisfied.

---

## Dependencies

- Upstream tasks: None
- Downstream tasks: WS3-A, WS3-D, WS4-A, WS1-D
- Runtime dependencies (routes/pipelines/config): `config/*.yaml` and `.env.example` must align with scripts and runtime defaults.
- Contract dependencies (schemas/interfaces): Config keys used by pipeline/backends and startup scripts.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS1-C
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

- Trigger conditions: Config key/path mismatch causing runtime drift.
- Rollback target maturity: `Implemented`
- Blocker owner: WS1 owner
- Re-promotion criteria: cross-file config/script/env drift checks pass.

---

## Residual Risks

- Config docs can drift from scripts over time. Owner: WS1. Mitigation: mandatory drift checks before promotion.
