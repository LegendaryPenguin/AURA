# Phase 2/3/4/5 Promotion Evidence

## Execution Run

- Date: 2026-04-26
- Scope: Phase 2 through Phase 5 closure evidence
- Workstreams: WS2 + WS3 + WS4

## Implemented Changes

- WS2:
  - Added camera subsystem modules (`useCamera`, `CameraView`, `CameraControls`, `device_utils`)
  - Added audio recorder module (`useAudioRecorder`)
  - Added WebSocket client/session modules (`socket`, `useWebSocket`, `useStreamingSession`)
- WS3:
  - Added `GET/POST` runtime streaming surfaces (`/stream`, `/agents/trigger`)
  - Added streaming pipeline and `segment`/`depth` stage modules
  - Updated orchestrator to return streaming pipeline for phase >=4
- WS4:
  - Added audio backend scaffold (`WhisperAudioBackend`)
  - Added segmentation backends (`SAM2SegmentationBackend`, `SAMHQSegmentationBackend`)
  - Added depth backends (`DepthAnythingBackend`, `MidasDepthBackend`)
  - Added tracker + track manager modules for session lifecycle

## Verification Artifacts

- `bash scripts/dev/run_tests.sh` -> pass
- `./.venv/bin/python -m pytest tests/unit/api/test_websocket_route.py tests/unit/pipeline/test_streaming_pipeline.py tests/unit/inference/test_audio_backend.py tests/unit/inference/test_segmentation_backends.py tests/unit/inference/test_depth_backends.py tests/unit/tracking/test_tracker_system.py -q` -> pass
- `./.venv/bin/python video-simulation/eval/evaluate_pipeline.py --strict --output metrics_strict.json` -> pass
- Consolidated gate runner:
  - `scripts/eval/run_phase2_to5_gates.sh`
  - includes default strict model binding: `VIDEO_SIM_VLM_MODEL_ID=Qwen/Qwen2.5-VL-3B-Instruct-AWQ`
- Execution artifact:
  - `artifacts/phase25_execution_20260426.json`

## Dependency Closure Statement

- Phase 2 required tasks: WS2-A/B/C/D/F, WS3-B/D, WS4-A/B/C are now at `Verified`.
- Phase 3 required tasks: WS2-A, WS3-B are now at `Verified`.
- Phase 4 required tasks: WS2-G/D, WS3-C/E, WS4-C/E are now at `Verified`.
- Phase 5 required tasks: WS2-E, WS3-E, WS4-D/E are now at `Verified`.

## Residual Risk + Owner

- Real-device performance variance for live camera streams can still differ from unit/integration environments.
- Owner: `Farrell`

## Sign-off

- WS2 sign-off: `Farrell`
- WS3 sign-off: `Farrell`
- WS4 sign-off: `Farrell`
