# WS1-B: Abstract Interfaces

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Done`                     |
| **Maturity** | `Implemented`            |
| **Owner**   | Nischay                    |
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

- [x] All abstract classes are importable with zero dependencies beyond stdlib and typing
- [x] A trivial concrete implementation can be written and instantiated (include a NoOp example in tests)
- [x] Type hints are complete — mypy passes with strict mode

---

## Dependencies

- Upstream tasks: None
- Downstream tasks: WS3-D, WS4-A, WS4-E
- Runtime dependencies (routes/pipelines/config): Implementers must satisfy interface contracts at runtime.
- Contract dependencies (schemas/interfaces): `shared/interfaces/*.py`

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS1-B
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

- Trigger conditions: Interface incompatibility with consumers.
- Rollback target maturity: `Implemented`
- Blocker owner: WS1 owner
- Re-promotion criteria: Interface contract tests pass for all dependent workstreams.

---

## Residual Risks

- Interface extensions may require staged adoption. Owner: WS1. Mitigation: append-only compatibility strategy.
