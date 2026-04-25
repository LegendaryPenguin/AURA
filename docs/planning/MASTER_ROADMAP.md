# AURA — MASTER ROADMAP

## Spatial AR Intelligence Platform

> **Source of truth for all agents.** Every agent must consult this document before starting work. Task assignments, file ownership, and phase gates are authoritative.

---

## Project Summary

Aura is a real-time spatial reasoning system that bridges physical environments and AI. Point a phone's camera at any object, ask a voice question, and Aura projects AR diagnostic overlays — bounding boxes, segmentation masks, and action prompts — directly onto that object's position in the live camera feed. All AI inference runs locally on the ASUS edge supercomputer. No cloud. No data leaves the room.

---

## Workstreams


| ID  | Name                         | Owns                                                                                | Purpose                                               |
| --- | ---------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------- |
| WS1 | Foundation & Contracts       | `shared/`, `config/`, `scripts/`, `server/utils/`, `tests/fixtures/`                | Schemas, interfaces, configs, mocks, utilities        |
| WS2 | Client Application           | `client/` (entire), `tests/unit/client/`                                            | React PWA — camera, audio, overlays, networking       |
| WS3 | Server API & Pipeline        | `server/main.py`, `server/api/`, `server/core/pipeline/`, `server/core/validation/` | FastAPI, routes, middleware, pipeline orchestration   |
| WS4 | Inference Engines & Tracking | `server/core/inference/`, `server/core/tracking/`, `server/agents/`                 | ML model integrations, SAM2 tracking, Fetch.ai agents |


---

## Phase Progression

### Phase 0 — Guaranteed Fallback

- **Deliverable:** Pre-recorded demo video + `Shift+F` hardcoded overlay injection
- **Proves:** Frontend rendering pipeline works independently of any server
- **Workstreams:** WS2 only
- **Status:** `Todo`

### Phase 1 — Static Image Analysis

- **Deliverable:** Upload photo → POST `/analyze` → VLM overlay rendered at correct coords
- **Proves:** Full inference pipeline (image → structured overlay response) works end-to-end
- **Pipeline:** `preprocess → analyze (VLM) → validate → postprocess`
- **Workstreams:** WS2-F, WS3-B, WS3-D, WS4-A
- **Status:** `Todo`

### Phase 2 — Live Camera + Voice + Snapshot AR *(Primary Target)*

- **Deliverable:** Live camera, hold-to-speak, JPEG + audio → `/analyze` → overlay snaps into place
- **Proves:** Full AR snapshot flow with voice query, SAM2 segmentation, <2s response
- **Pipeline:** `preprocess → transcribe → analyze (VLM) → segment (SAM2) → validate → postprocess`
- **Milestone:** 80%+ overlays land correctly across 20 test captures
- **Workstreams:** WS2-A/B/C/D/F, WS3-B/D, WS4-A/B/C
- **Status:** `Todo`

### Phase 3 — Continuous Auto-Scan

- **Deliverable:** Auto-scan toggle fires snapshot every 2.5s, server drops concurrent requests (429)
- **Proves:** System handles periodic re-inference gracefully
- **Workstreams:** WS2-A (toggle), WS3-B (rate limiting) — reuses Phase 2
- **Status:** `Todo`

### Phase 4 — SAM2-Tracked Continuous AR

- **Deliverable:** WebSocket `/stream`, SAM2 VideoPredictor tracks objects between VLM queries
- **Proves:** AR overlays track moving objects at frame rate without per-frame VLM inference
- **Pipeline:** Initial: `VLM → SAM2 seed → tracker init` / Subsequent: `SAM2 propagate → depth → overlay`
- **Workstreams:** WS2-G/D, WS3-C/E, WS4-C/E
- **Status:** `Todo`

### Phase 5 — Full Real-Time Streaming AR

- **Deliverable:** Persistent WebSocket, SAM2 + Depth Anything v2 on every frame, depth sorting, hallucination rejection
- **Proves:** Closest approximation to true real-time AR within local hardware budget
- **Workstreams:** WS2-E, WS3-E, WS4-D/E — reuses Phase 4
- **Status:** `Todo`

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


| Task  | Workstream | Summary                       | Files | Phase       | Status      |
| ----- | ---------- | ----------------------------- | ----- | ----------- | ----------- |
| WS1-A | Foundation | Schemas & TypeScript types    | 5     | Sprint 0    | Done        |
| WS1-B | Foundation | Abstract interfaces           | 3     | Sprint 0    | Done        |
| WS1-C | Foundation | Config & environment          | 6     | Sprint 0    | Done        |
| WS1-D | Foundation | Scripts & mock server         | 10    | Sprint 0    | Done        |
| WS1-E | Foundation | Utilities & test fixtures     | 8+    | Sprint 0    | Done        |
| WS2-A | Client     | Camera subsystem              | 4     | Phase 2     | Todo        |
| WS2-B | Client     | Audio subsystem               | 1     | Phase 2     | Todo        |
| WS2-C | Client     | Frame capture & coords        | 3     | Phase 1     | Todo        |
| WS2-D | Client     | Overlay rendering             | 6     | Phase 1     | Todo        |
| WS2-E | Client     | UI chrome & fallback          | 8     | Phase 0     | Done        |
| WS2-F | Client     | REST networking               | 3     | Phase 1     | Todo        |
| WS2-G | Client     | WebSocket networking          | 3     | Phase 4     | Todo        |
| WS2-H | Client     | App shell & integration       | 6     | Integration | Done        |
| WS3-A | Server API | FastAPI scaffold & middleware | 4     | Phase 1     | Done        |
| WS3-B | Server API | REST routes                   | 4     | Phase 1     | In-Progress |
| WS3-C | Server API | WebSocket route               | 2     | Phase 4     | Todo        |
| WS3-D | Server API | Snapshot pipeline & stages    | 7     | Phase 1     | Todo        |
| WS3-E | Server API | Streaming pipeline            | 3     | Phase 4     | Todo        |
| WS3-F | Server API | Validation                    | 3     | Phase 1     | Todo        |
| WS4-A | Inference  | VLM backend                   | 3     | Phase 1     | In-Progress |
| WS4-B | Inference  | Audio backend                 | 2     | Phase 2     | Todo        |
| WS4-C | Inference  | Segmentation backend          | 3     | Phase 2     | Todo        |
| WS4-D | Inference  | Depth backend                 | 3     | Phase 5     | Todo        |
| WS4-E | Inference  | Tracking system               | 3     | Phase 4     | Todo        |
| WS4-F | Inference  | Generation & agents           | 5     | Stretch     | Todo        |


---

## Cross-Workstream Rules

1. All cross-boundary calls go through interfaces in `shared/interfaces/`
2. Schema changes to `shared/schemas/` require RFC sign-off from all affected workstreams
3. Schemas are append-only: add fields, never remove or rename
4. WS2 → WS3 communication is HTTP/WebSocket only — no code imports
5. WS4 has zero knowledge of routes or pipelines
6. Contract tests run on every PR merge

---

## Task File Location

Individual task definitions with scope, verification, and ownership: `docs/planning/tasks/`