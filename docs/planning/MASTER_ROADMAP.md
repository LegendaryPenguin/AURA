# AURA — MASTER ROADMAP

## Spatial AR Intelligence Platform

> **Source of truth for all agents.** Every agent must consult this document before starting work. Task assignments, file ownership, and phase gates are authoritative.

---

## Project Summary

Aura is a real-time spatial reasoning system that bridges physical environments and AI. Point a phone's camera at any object, ask a voice question, and Aura projects AR diagnostic overlays — bounding boxes, segmentation masks, and action prompts — directly onto that object's position in the live camera feed. All AI inference runs locally on the ASUS edge supercomputer. No cloud. No data leaves the room.

---

## Alignment Governance (Authoritative)

This roadmap defines delivery truth. Task files and workflow checklist execution must remain consistent with this section.

### Truth Layers (Precedence)

Status claims are valid only when all layers align:

1. **Capability truth**: phase behavior is user-visible and demonstrable.
2. **Contract truth**: route and interface payloads match shared contracts.
3. **Runtime truth**: config/env/script/runtime defaults are consistent.
4. **Verification truth**: required gates pass with evidence.

Verification truth validates runtime truth, runtime truth implements contract truth, and contract truth supports capability truth.

### Maturity Model (Required)

Keep legacy task `Status` for compatibility, but all tasks and phases must also use `Maturity`:

- `Planned`
- `Implemented`
- `Integrated`
- `Verified`
- `DemoReady`

Rules:

- Promotion is monotonic (no skipping levels).
- Regression after promotion requires immediate rollback by at least one maturity level.
- A task marked `Status: Done` can still be below `Maturity: Verified` during migration.

### Phase Closure Rule

A phase cannot be marked complete unless:

- all required tasks for that phase are at least `Maturity: Verified`,
- phase acceptance checks pass,
- promotion evidence is recorded,
- affected workstreams sign off.

### Phase Closure Matrix

| Phase | Required Task Maturity Floor | Additional Closure Evidence |
| --- | --- | --- |
| Phase 0 | All required tasks `Verified` | Fallback demo path reproducible |
| Phase 1 | All required tasks `Verified` | Integration gate `tests/integration/test_phase1_e2e.py` passing |
| Phase 2 | All required tasks `Verified` | 20-capture overlay quality + latency evidence |
| Phase 3 | All required tasks `Verified` | Periodic auto-scan + 429 drop behavior validated |
| Phase 4 | All required tasks `Verified` | WebSocket + SAM2 tracking E2E evidence |
| Phase 5 | All required tasks `Verified` | Streaming stability evidence and fallback readiness |

---

## Workstreams


| ID  | Name                         | Owns                                                                                                                 | Purpose                                               |
| --- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| WS1 | Foundation & Contracts       | `shared/`, `config/`, `scripts/`, `server/utils/`, `tests/fixtures/`                                                 | Schemas, interfaces, configs, mocks, utilities        |
| WS2 | Client Application           | `client/` (entire), `tests/unit/client/`                                                                             | React PWA — camera, audio, overlays, networking       |
| WS3 | Server API & Pipeline        | `server/main.py`, `server/api/`, `server/core/pipeline/`, `server/core/validation/`                                  | FastAPI, routes, middleware, pipeline orchestration   |
| WS4 | Inference Engines & Tracking | `server/core/inference/`, `server/core/tracking/`, `server/agents/`, `tests/unit/inference/`, `tests/unit/tracking/` | ML model integrations, SAM2 tracking, Fetch.ai agents |


---

## Phase Progression

### Phase 0 — Guaranteed Fallback

- **Deliverable:** Pre-recorded demo video + `Shift+F` hardcoded overlay injection
- **Proves:** Frontend rendering pipeline works independently of any server
- **Workstreams:** WS2 only
- **Status:** `Done`
- **Required task maturity:** WS2-E `Verified` + WS2-H `Integrated`

### Phase 1 — Static Image Analysis

- **Deliverable:** Upload photo → POST `/analyze` → VLM overlay rendered at correct coords
- **Proves:** Full inference pipeline (image → structured overlay response) works end-to-end
- **Pipeline:** `preprocess → transcribe → analyze (VLM) → postprocess`
- **Workstreams:** WS2-F, WS3-B, WS3-D, WS4-A
- **Status:** `In-Progress` (automated integration gate below passes; on-device VLM quality bar still needs real-model validation)
- **Integration gate:** `tests/integration/test_phase1_e2e.py` must pass — TestClient against `create_app()` POSTs to `/analyze` with valid `image_base64` + `query`, verifies 200 response with schema-valid overlay fields. **Current:** gate implemented and passing in CI.
- **Required task maturity:** WS2-C/D/F `Verified`, WS2-H `Integrated`, WS3-A/B/D/F `Verified`, WS4-A `Verified`

### Phase 2 — Live Camera + Voice + Snapshot AR *(Primary Target)*

- **Deliverable:** Live camera, hold-to-speak, JPEG + audio → `/analyze` → overlay snaps into place
- **Proves:** Full AR snapshot flow with voice query, SAM2 segmentation, <2s response
- **Pipeline:** `preprocess → transcribe → analyze (VLM) → segment (SAM2) → validate → postprocess`
- **Milestone:** 80%+ overlays land correctly across 20 test captures
- **Workstreams:** WS2-A/B/C/D/F, WS3-B/D, WS4-A/B/C
- **Status:** `Todo`
- **Required task maturity:** WS2-A/B/C/D/F `Verified`, WS3-B/D `Verified`, WS4-A/B/C `Verified`

### Phase 3 — Continuous Auto-Scan

- **Deliverable:** Auto-scan toggle fires snapshot every 2.5s, server drops concurrent requests (429)
- **Proves:** System handles periodic re-inference gracefully
- **Workstreams:** WS2-A (toggle), WS3-B (rate limiting) — reuses Phase 2
- **Status:** `Todo`
- **Required task maturity:** WS2-A `Verified`, WS3-B `Verified`

### Phase 4 — SAM2-Tracked Continuous AR

- **Deliverable:** WebSocket `/stream`, SAM2 VideoPredictor tracks objects between VLM queries
- **Proves:** AR overlays track moving objects at frame rate without per-frame VLM inference
- **Pipeline:** Initial: `VLM → SAM2 seed → tracker init` / Subsequent: `SAM2 propagate → depth → overlay`
- **Workstreams:** WS2-G/D, WS3-C/E, WS4-C/E
- **Status:** `Todo`
- **Required task maturity:** WS2-G/D `Verified`, WS3-C/E `Verified`, WS4-C/E `Verified`

### Phase 5 — Full Real-Time Streaming AR

- **Deliverable:** Persistent WebSocket, SAM2 + Depth Anything v2 on every frame, depth sorting, hallucination rejection
- **Proves:** Closest approximation to true real-time AR within local hardware budget
- **Workstreams:** WS2-E, WS3-E, WS4-D/E — reuses Phase 4
- **Status:** `Todo`
- **Required task maturity:** WS2-E `Verified`, WS3-E `Verified`, WS4-D/E `Verified`

---

## Sprint Timeline


| Sprint | Days  | Focus              | Max Parallel Agents | Gate                                                      |
| ------ | ----- | ------------------ | ------------------- | --------------------------------------------------------- |
| 0      | 1–2   | Foundation (WS1)   | 5                   | Mock server running, schemas defined, contract tests pass |
| 1      | 3–6   | Phase 0–2 features | 12                  | Phase 2 E2E passes: camera → voice → overlay              |
| 2      | 7–9   | Phase 3–4 features | 6                   | Phase 4 E2E passes: WebSocket → tracked overlay           |
| 3      | 10–11 | Phase 5 + polish   | 4                   | Phase 5 stable or fallback to Phase 4                     |


---

## Agent Tasks — Quick Reference


| Task  | Workstream | Summary                                      | Files | Phase       | Status |
| ----- | ---------- | -------------------------------------------- | ----- | ----------- | ------ |
| WS1-A | Foundation | Schemas & TypeScript types                   | 5     | Sprint 0    | Done   |
| WS1-B | Foundation | Abstract interfaces                          | 3     | Sprint 0    | Done   |
| WS1-C | Foundation | Config & environment                         | 6     | Sprint 0    | Done   |
| WS1-D | Foundation | Scripts & mock server                        | 10    | Sprint 0    | Done   |
| WS1-E | Foundation | Utilities & test fixtures                    | 8+    | Sprint 0    | Done   |
| WS2-A | Client     | Camera subsystem                             | 4     | Phase 2     | Todo   |
| WS2-B | Client     | Audio subsystem                              | 1     | Phase 2     | Todo   |
| WS2-C | Client     | Frame capture & coords                       | 3     | Phase 1     | Done   |
| WS2-D | Client     | Overlay rendering                            | 6     | Phase 1     | Done   |
| WS2-E | Client     | UI chrome & fallback                         | 8     | Phase 0     | Done   |
| WS2-F | Client     | REST networking                              | 3     | Phase 1     | Done   |
| WS2-G | Client     | WebSocket networking                         | 3     | Phase 4     | Todo   |
| WS2-H | Client     | App shell & integration (depends: WS2-C/D/F) | 6     | Integration | Done   |
| WS3-A | Server API | FastAPI scaffold & middleware                | 4     | Phase 1     | Done   |
| WS3-B | Server API | REST routes                                  | 4     | Phase 1     | Done   |
| WS3-C | Server API | WebSocket route                              | 2     | Phase 4     | Todo   |
| WS3-D | Server API | Snapshot pipeline & stages                   | 7     | Phase 1     | Done   |
| WS3-E | Server API | Streaming pipeline                           | 3     | Phase 4     | Todo   |
| WS3-F | Server API | Validation                                   | 3     | Phase 1     | Done   |
| WS4-A | Inference  | VLM backend + 20-image benchmark harness     | 6     | Phase 1     | Done   |
| WS4-B | Inference  | Audio backend                                | 3     | Phase 2     | Todo   |
| WS4-C | Inference  | Segmentation backend                         | 4     | Phase 2     | Todo   |
| WS4-D | Inference  | Depth backend                                | 4     | Phase 5     | Todo   |
| WS4-E | Inference  | Tracking system                              | 4     | Phase 4     | Todo   |
| WS4-F | Inference  | Generation & agents                          | 6     | Stretch     | Todo   |


---

## Cross-Workstream Rules

1. All cross-boundary calls go through interfaces in `shared/interfaces/`
2. Schema changes to `shared/schemas/` require RFC sign-off from all affected workstreams
3. Schemas are append-only: add fields, never remove or rename
4. WS2 → WS3 communication is HTTP/WebSocket only — no code imports
5. WS4 has zero knowledge of routes or pipelines
6. Contract tests run on every PR merge
7. HTTP contract tests: every route handler must have a contract test that validates request/response payloads against `shared/schemas/*.json`
8. PipelineContext field contract: route code must set `context.query` for text queries and `context.response` for binary payloads (image_base64, audio_base64) and inter-stage results — see docstring in `shared/interfaces/pipeline_stage.py`
9. `WORKFLOW_CHECKLIST.md` is the operational gate. Missing required completion fields means `DoNotPromote`.
10. Phase status cannot exceed the lowest required task maturity for that phase.
11. Config authority drift checks are mandatory before `Integrated -> Verified` promotion (check `config/*.yaml`, `.env.example`, startup scripts, and documented defaults).
12. Route contract coverage must map one-to-one with public routes listed in roadmap scope.

---

## Promotion Evidence (Required)

Every maturity promotion beyond `Implemented` must include:

- change summary,
- gates executed,
- evidence links/artifacts,
- dependency closure statement,
- residual risk and owner,
- sign-off from affected workstream owners.

---

## Migration Policy (Status -> Maturity)

During governance rollout:

- Existing tasks may keep current `Status`.
- Each task must add `Maturity` at next touch.
- If `Status: Done` but gates are incomplete, set `Maturity` to the highest proven level and add a migration note.
- Roadmap phase claims must follow maturity gates immediately, even before all task files are fully migrated.

---

## Task File Location

Individual task definitions with scope, verification, and ownership: `docs/planning/tasks/`

---

## Retrospective — why Phase 1 had integration blockers

1. **Isolated “Done” without a consumer:** WS3-B, WS3-D, and client networking were each verified with mocks, but no single test walked the same JSON payload from `shared/schemas/analysis_request.json` through `POST /analyze` into the snapshot pipeline. That allowed field-name drift between route handlers and `PipelineContext` until caught.
2. **Composition root (WS3-A) was underspecified in verification:** `server/main.py` must mount routes *and* attach `app.state.snapshot_pipeline` for anything to render beyond empty fallbacks; early checklists did not require an OpenAPI or TestClient check for `/analyze` on the real `create_app()`.
3. **App shell vs. feature hooks:** the shell shipped before the REST hook layer was the single path to the API; the roadmap now ties WS2-H to WS2-C/D/F explicitly.
4. **Resolution in repo:** add `tests/integration/test_phase1_e2e.py` as the Phase 1 **integration gate**, extend `scripts/dev/run_tests.sh` to run `tests/integration/`, and keep rules 7–8 (HTTP contract + `PipelineContext` field contract) as standing guardrails.