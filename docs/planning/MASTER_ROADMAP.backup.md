# AURA — MASTER ROADMAP (Backup Copy)

## Spatial AR Intelligence Platform

> Backup copy of `MASTER_ROADMAP.md`. If the primary file is unexpectedly emptied, restore from this file.

---

## Project Summary

Aura is a real-time spatial reasoning system that bridges physical environments and AI. Point a phone's camera at any object, ask a voice question, and Aura projects AR diagnostic overlays — bounding boxes, segmentation masks, and action prompts — directly onto that object's position in the live camera feed. All AI inference runs locally on the ASUS edge supercomputer. No cloud. No data leaves the room.

---

## Workstreams


| ID  | Name                         | Owns                                                                                                                 | Purpose                                               |
| --- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| WS1 | Foundation & Contracts       | `shared/`, `config/`, `scripts/`, `server/utils/`, `tests/fixtures/`                                                 | Schemas, interfaces, configs, mocks, utilities        |
| WS2 | Client Application           | `client/` (entire), `tests/unit/client/`                                                                             | React PWA — camera, audio, overlays, networking       |
| WS3 | Server API & Pipeline        | `server/main.py`, `server/api/`, `server/core/pipeline/`, `server/core/validation/`                                  | FastAPI, routes, middleware, pipeline orchestration   |
| WS4 | Inference Engines & Tracking | `server/core/inference/`, `server/core/tracking/`, `server/agents/`, `tests/unit/inference/`, `tests/unit/tracking/` | ML model integrations, SAM2 tracking, Fetch.ai agents |


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
| WS4-A | Inference  | VLM backend                   | 4     | Phase 1     | In-Progress |
| WS4-B | Inference  | Audio backend                 | 3     | Phase 2     | Todo        |
| WS4-C | Inference  | Segmentation backend          | 4     | Phase 2     | Todo        |
| WS4-D | Inference  | Depth backend                 | 4     | Phase 5     | Todo        |
| WS4-E | Inference  | Tracking system               | 4     | Phase 4     | Todo        |
| WS4-F | Inference  | Generation & agents           | 6     | Stretch     | Todo        |
