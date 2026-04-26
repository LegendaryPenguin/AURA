# AURA — Spatial AR Intelligence Platform

Real-time spatial reasoning that bridges physical environments and AI. Point a phone's camera at any object, ask a voice question, and Aura projects AR diagnostic overlays — bounding boxes, segmentation masks, and action prompts — directly onto that object's position in the live camera feed.

**All AI inference runs locally on the ASUS edge supercomputer. No cloud. No data leaves the room.**



---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  SEMANTIC LANE (slow, smart)                                │
│  Whisper → Qwen2.5-VL → bbox + label       (on trigger)    │
└──────────────────────────────────────────┬──────────────────┘
                                           │ seeds
┌──────────────────────────────────────────▼──────────────────┐
│  TRACKING LANE (fast, spatial)                              │
│  SAM2 VideoPredictor → updated mask        (every frame)    │
│  Depth Anything v2 → depth map             (parallel)       │
└─────────────────────────────────────────────────────────────┘
```

The VLM fires once to understand the scene. SAM2 fires every frame to keep overlays locked to objects as the camera moves. Real-time AR emerges from their combination.

---

## Tech Stack


| Layer        | Choice                            | Purpose                               |
| ------------ | --------------------------------- | ------------------------------------- |
| Hardware     | ASUS Ascent GX10 (GB10 Blackwell) | Local inference, 128GB unified mem    |
| VLM          | Qwen2.5-VL-7B via vLLM            | Spatial reasoning + JSON output       |
| Segmentation | SAM2                              | Pixel-accurate masks + video tracking |
| Depth        | Depth Anything v2                 | Monocular depth estimation            |
| Audio        | Whisper-base                      | Voice transcription                   |
| Backend      | FastAPI (Python)                  | REST + WebSocket API                  |
| Frontend     | React PWA (TypeScript, Vite)      | Camera, overlays, AR rendering        |
| SSL          | mkcert                            | HTTPS for mobile camera access        |


---

## Project Structure

```
aura/
├── config/              # Runtime YAML configuration
├── shared/              # Cross-workstream contracts (schemas + interfaces)
├── server/              # FastAPI backend + inference + pipeline
│   ├── api/             # HTTP and WebSocket routes
│   ├── core/            # Inference backends, pipeline, tracking, validation
│   ├── agents/          # Fetch.ai uAgents (stretch)
│   └── utils/           # Shared server utilities
├── client/              # React PWA frontend
│   └── src/
│       ├── components/  # Camera, overlays, UI chrome
│       ├── hooks/       # React hooks
│       ├── services/    # API + WebSocket clients
│       └── utils/       # Coordinate mapping, device detection
├── tests/               # Unit, contract, and integration tests
├── scripts/             # Setup, startup, and dev scripts
└── docs/planning/       # Task definitions and roadmap
```

---

## Progressive Phases


| Phase | Name                           | Description                                                     |
| ----- | ------------------------------ | --------------------------------------------------------------- |
| 0     | Guaranteed Fallback            | Pre-recorded video + hardcoded overlay (cannot fail)            |
| 1     | Static Image Analysis          | Upload photo → VLM → overlay at correct coords                  |
| 2     | Live Camera + Voice *(target)* | Camera + voice → snapshot pipeline → AR overlay (<2s)           |
| 3     | Continuous Auto-Scan           | Auto-scan every 2.5s, server drops concurrent (429)             |
| 4     | SAM2-Tracked AR                | WebSocket streaming, SAM2 tracks objects between VLM queries    |
| 5     | Full Real-Time Streaming       | SAM2 + Depth on every frame, depth sorting, hallucination check |


Each phase is independently demonstrable. A polished earlier phase beats a broken later phase.

---

## Quick Start

### Prerequisites

- ASUS Ascent GX10 (or NVIDIA GPU with 24GB+ VRAM)
- Python 3.11+
- Node.js 20+
- mkcert

### Setup

```bash
# 1. Install dependencies
scripts/setup/install_server_deps.sh
scripts/setup/install_client_deps.sh

# 2. Configure HTTPS (required for mobile camera)
scripts/setup/setup_ssl.sh

# 3. Download model weights
scripts/setup/download_models.sh

# 4. Start services
scripts/startup/start_vllm.sh          # vLLM on port 8000
scripts/startup/start_server.sh        # FastAPI on port 8443
scripts/startup/warmup_all.sh          # Wait for models to warm up

# 5. Verify
curl https://<local-ip>:8443/health
```

### Development (No GPU Required)

```bash
# Start mock server (returns canned responses)
scripts/dev/run_mock_server.sh

# Run all tests
scripts/dev/run_tests.sh
```

---

## Workstreams

Development is organized into 4 parallel workstreams with strict directory ownership:

- **WS1 — Foundation:** Schemas, interfaces, configs, utilities, mock server
- **WS2 — Client:** React PWA, camera, audio, overlays, networking
- **WS3 — Server API:** FastAPI, routes, pipeline orchestration, validation
- **WS4 — Inference:** VLM, SAM2, Depth, Whisper, tracking state machine

See `docs/planning/MASTER_ROADMAP.md` for full task breakdown and status tracking.

---

## Testing

```bash
# Unit tests (no GPU required)
pytest tests/unit/ -v
cd client && npx vitest run

# Contract tests (schema + interface compliance)
pytest tests/contract/ -v

# Integration tests (requires server)
pytest tests/integration/ -v
```

---

## License

Private — All rights reserved.