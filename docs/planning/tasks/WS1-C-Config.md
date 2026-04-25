# WS1-C: Config Files & Environment

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Todo`                     |
| **Owner**   | _Unassigned_               |
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

- [ ] YAML files parse without error (validate with `pyyaml`)
- [ ] `config_loader.py` (WS1-E) successfully loads and validates each file
- [ ] All referenced file paths in config have clear documentation on expected contents
