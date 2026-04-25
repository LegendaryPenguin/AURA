# WS4-F: Generation & Agents (Stretch)

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Owner**   | _Unassigned_                     |
| **Phase**   | Stretch                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/inference/generation/__init__.py`
- `server/core/inference/generation/sdxl_turbo.py`
- `server/agents/__init__.py`
- `server/agents/base_agent.py`
- `server/agents/fetch_agent.py`
- `tests/unit/inference/test_generation_and_agents.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `sdxl_turbo.py`: implement `InferenceBackend` for SDXL-Turbo. `generate(prompt) → image_b64`. 4-step diffusion.
- `fetch_agent.py`: uAgent triggered by HTTP call when overlay's `action_required` is True. Simulate ASI network lookup. Return mock procurement result.
- Both are stretch goals — disable cleanly via config. Core demo stands alone without them.

---

## Verification

- [ ] `sdxl_turbo.py`: `generate()` returns valid base64-encoded image
- [ ] `fetch_agent.py`: returns structured procurement result matching expected schema
- [ ] Both can be disabled via `config/models.yaml` without affecting any other system
- [ ] Unit test: disabled backends return `None` gracefully, enabled backends return valid data
