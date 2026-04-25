# WS1-B: Abstract Interfaces

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Todo`                     |
| **Owner**   | _Unassigned_               |
| **Sprint**  | Sprint 0 (Foundation)      |
| **Stream**  | WS1 — Foundation & Contracts |

---

## Scope — Owned Files

- `shared/interfaces/inference_base.py`
- `shared/interfaces/pipeline_stage.py`
- `shared/interfaces/tracker_base.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `InferenceBackend`: abstract methods `load()`, `warmup()`, `is_ready() → bool`, plus domain-specific inference method signatures
- `PipelineStage`: abstract `execute(context: PipelineContext) → PipelineContext`
- `TrackerBackend`: abstract `seed(mask)`, `propagate(frame) → mask`, `reset()`, `state → Enum`
- Define `PipelineContext` dataclass holding all inter-stage data (image, query, bbox, mask, depth_map, response)

---

## Verification

- [ ] All abstract classes are importable with zero dependencies beyond stdlib and typing
- [ ] A trivial concrete implementation can be written and instantiated (include a NoOp example in tests)
- [ ] Type hints are complete — mypy passes with strict mode
