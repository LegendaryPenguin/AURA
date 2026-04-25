# WS3-E: Streaming Pipeline & Segment/Depth Stages

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Todo`                        |
| **Maturity** | `Planned`                   |
| **Owner**   | _Unassigned_                  |
| **Phase**   | Phase 4                       |
| **Stream**  | WS3 — Server API & Pipeline   |

---

## Scope — Owned Files

- `server/core/pipeline/streaming_pipeline.py`
- `server/core/pipeline/stages/segment.py`
- `server/core/pipeline/stages/depth.py`
- `tests/unit/pipeline/test_streaming_pipeline.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `streaming_pipeline.py`: route first frame through semantic lane (VLM + SAM2 seed), subsequent frames through tracking lane (SAM2 propagate + depth). Fire VLM re-query in background on configurable interval. Frame-drop logic: skip frames older than threshold from `config/pipeline.yaml`.
- `segment.py`: call segmentation backend with VLM bounding box → mask. Attach mask to `PipelineContext`.
- `depth.py`: call depth backend → depth map. Run async — never blocks overlay delivery. Attach depth data to `PipelineContext`.

---

## Verification

- [ ] With mock backends: streaming pipeline processes first frame through semantic lane, subsequent through tracking lane
- [ ] Segment stage converts VLM bbox to mask in `PipelineContext`
- [ ] Depth stage runs async and does not block overlay delivery (test with slow mock)
- [ ] Frame-drop logic: old frames are dropped, fresh frames are processed
- [ ] VLM re-query fires on configured interval during streaming
- [ ] Unit test: streaming pipeline state machine transitions: INIT → SEMANTIC → TRACKING → RE-QUERY

---

## Dependencies

- Upstream tasks: WS4-C, WS4-D, WS4-E
- Downstream tasks: WS3-C, WS2-G
- Runtime dependencies (routes/pipelines/config): streaming pipeline orchestration and queue/drop policy.
- Contract dependencies (schemas/interfaces): stage interfaces and streaming response payload contracts.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS3-E
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

- Trigger conditions: streaming lane regressions or async stage blocking behavior.
- Rollback target maturity: `Implemented`
- Blocker owner: WS3 owner
- Re-promotion criteria: streaming verification and state-machine tests pass.

---

## Residual Risks

- Throughput/performance behavior may vary under realistic frame load. Owner: WS3. Mitigation: load-oriented tests.
