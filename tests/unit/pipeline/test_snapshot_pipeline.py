"""Unit tests for WS3-D: Snapshot Pipeline & Stages."""

from __future__ import annotations

import base64
import io
import time
from typing import Any

import pytest
from PIL import Image

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage
from server.core.pipeline.snapshot_pipeline import PipelineTimeoutError, SnapshotPipeline
from server.core.pipeline.orchestrator import build_snapshot_pipeline, get_pipeline
from server.core.pipeline.stages.preprocess import PreprocessStage
from server.core.pipeline.stages.transcribe import TranscribeStage
from server.core.pipeline.stages.analyze import AnalyzeStage
from server.core.pipeline.stages.postprocess import PostprocessStage
from server.utils.image_utils import encode_jpeg
from tests.fixtures.mocks.mock_inference_backend import MockInferenceBackend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg_b64(width: int = 100, height: int = 100) -> str:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    return base64.b64encode(encode_jpeg(img)).decode()


def _make_png_b64() -> str:
    img = Image.new("RGB", (50, 50), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _pipeline_config(**overrides: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "orchestrator": {"phase": 1, "include_timing_metadata": False},
        "timeouts": {
            "total_request_timeout_ms": 5000,
            "preprocess_ms": 500,
            "transcribe_ms": 800,
            "analyze_ms": 1200,
            "postprocess_ms": 500,
        },
        "preprocess": {
            "expected_image_format": "jpeg",
            "target_width": 640,
            "target_height": 480,
            "keep_aspect_ratio": True,
            "max_image_bytes": 4_194_304,
        },
        "snapshot": {
            "default_query": "What am I looking at?",
            "save_debug_artifacts": False,
        },
    }
    cfg.update(overrides)
    return cfg


def _vlm_backend(**kwargs: Any) -> MockInferenceBackend:
    backend = MockInferenceBackend()
    backend.load()

    def patched_analyze(image: bytes, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "overlays": [
                {
                    "bbox": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.3},
                    "label": "test object",
                    "confidence": 0.95,
                    "ui_layer": "foreground",
                    "overlay_type": "diagnostic",
                    "action_required": False,
                }
            ],
            **kwargs,
        }

    backend.analyze = patched_analyze  # type: ignore[assignment]
    return backend


# ---------------------------------------------------------------------------
# Preprocess stage
# ---------------------------------------------------------------------------

class TestPreprocessStage:
    def test_rejects_non_jpeg(self) -> None:
        stage = PreprocessStage(_pipeline_config())
        ctx = PipelineContext(response={"image_base64": _make_png_b64()})
        with pytest.raises(ValueError, match="JPEG"):
            stage.execute(ctx)

    def test_rejects_missing_image(self) -> None:
        stage = PreprocessStage(_pipeline_config())
        ctx = PipelineContext(response={})
        with pytest.raises(ValueError, match="missing image_base64"):
            stage.execute(ctx)

    def test_resizes_to_configured_dimensions(self) -> None:
        stage = PreprocessStage(_pipeline_config())
        ctx = PipelineContext(response={"image_base64": _make_jpeg_b64(100, 100)})
        result = stage.execute(ctx)

        assert result.image is not None
        from server.utils.image_utils import decode_jpeg
        out = decode_jpeg(result.image)
        assert out.size == (640, 480)

    def test_rejects_oversized_image(self) -> None:
        cfg = _pipeline_config()
        cfg["preprocess"]["max_image_bytes"] = 10
        stage = PreprocessStage(cfg)
        ctx = PipelineContext(response={"image_base64": _make_jpeg_b64()})
        with pytest.raises(ValueError, match="exceeds limit"):
            stage.execute(ctx)


# ---------------------------------------------------------------------------
# Transcribe stage
# ---------------------------------------------------------------------------

class TestTranscribeStage:
    def test_fallback_when_no_audio(self) -> None:
        backend = MockInferenceBackend()
        backend.load()
        stage = TranscribeStage(backend, _pipeline_config())
        ctx = PipelineContext(response={})
        result = stage.execute(ctx)
        assert result.query == "What am I looking at?"

    def test_fallback_when_audio_empty(self) -> None:
        backend = MockInferenceBackend()
        backend.load()
        stage = TranscribeStage(backend, _pipeline_config())
        ctx = PipelineContext(response={"audio_base64": base64.b64encode(b"").decode()})
        result = stage.execute(ctx)
        assert result.query == "What am I looking at?"

    def test_uses_transcript_when_audio_present(self) -> None:
        backend = MockInferenceBackend()
        backend.load()
        stage = TranscribeStage(backend, _pipeline_config())
        audio_b64 = base64.b64encode(b"some audio data").decode()
        ctx = PipelineContext(response={"audio_base64": audio_b64})
        result = stage.execute(ctx)
        assert result.query == "mock transcript"

    def test_fallback_on_transcription_error(self) -> None:
        backend = MockInferenceBackend()
        backend.load()
        backend.transcribe = lambda audio: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[assignment]
        stage = TranscribeStage(backend, _pipeline_config())
        audio_b64 = base64.b64encode(b"some audio data").decode()
        ctx = PipelineContext(response={"audio_base64": audio_b64})
        result = stage.execute(ctx)
        assert result.query == "What am I looking at?"


# ---------------------------------------------------------------------------
# Analyze stage
# ---------------------------------------------------------------------------

class TestAnalyzeStage:
    def test_calls_backend_and_stores_result(self) -> None:
        backend = _vlm_backend()
        stage = AnalyzeStage(backend, _pipeline_config())
        ctx = PipelineContext(image=b"fake-jpeg", query="describe this", response={})
        result = stage.execute(ctx)
        assert result.response is not None
        assert "vlm_result" in result.response
        assert result.response["vlm_result"]["query"] == "describe this"

    def test_raises_without_image(self) -> None:
        backend = _vlm_backend()
        stage = AnalyzeStage(backend, _pipeline_config())
        ctx = PipelineContext(image=None, query="describe this")
        with pytest.raises(ValueError, match="no preprocessed image"):
            stage.execute(ctx)

    def test_uses_default_query_when_empty(self) -> None:
        backend = _vlm_backend()
        stage = AnalyzeStage(backend, _pipeline_config())
        ctx = PipelineContext(image=b"fake-jpeg", query="", response={})
        result = stage.execute(ctx)
        assert result.response["vlm_result"]["query"] == "What am I looking at?"


# ---------------------------------------------------------------------------
# Postprocess stage
# ---------------------------------------------------------------------------

class TestPostprocessStage:
    def test_valid_vlm_output_produces_overlay_response(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={
            "request_id": "req-1",
            "session_id": "sess-1",
            "vlm_result": {
                "overlays": [
                    {
                        "bbox": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.3},
                        "label": "widget",
                        "confidence": 0.9,
                        "ui_layer": "foreground",
                        "overlay_type": "info",
                        "action_required": True,
                    }
                ],
            },
        })
        result = stage.execute(ctx)
        payload = result.response
        assert payload["request_id"] == "req-1"
        assert payload["session_id"] == "sess-1"
        assert "created_at" in payload
        assert len(payload["overlays"]) == 1
        assert payload["overlays"][0]["label"] == "widget"

    def test_rejects_missing_vlm_result(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={})
        with pytest.raises(ValueError, match="no vlm_result"):
            stage.execute(ctx)

    def test_rejects_missing_overlay_fields(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={
            "vlm_result": {
                "overlays": [{"bbox": {"x": 0, "y": 0, "width": 0.5, "height": 0.5}, "label": "x"}],
            },
        })
        with pytest.raises(ValueError, match="overlay missing keys"):
            stage.execute(ctx)

    def test_rejects_invalid_bbox_range(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={
            "vlm_result": {
                "overlays": [
                    {
                        "bbox": {"x": 1.5, "y": 0.2, "width": 0.5, "height": 0.3},
                        "label": "bad",
                        "confidence": 0.9,
                        "ui_layer": "foreground",
                        "overlay_type": "info",
                        "action_required": False,
                    }
                ],
            },
        })
        with pytest.raises(ValueError, match="bbox.x must be in"):
            stage.execute(ctx)

    def test_rejects_invalid_ui_layer(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={
            "vlm_result": {
                "overlays": [
                    {
                        "bbox": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.3},
                        "label": "obj",
                        "confidence": 0.9,
                        "ui_layer": "invalid_layer",
                        "overlay_type": "info",
                        "action_required": False,
                    }
                ],
            },
        })
        with pytest.raises(ValueError, match="invalid ui_layer"):
            stage.execute(ctx)

    def test_passes_model_version_and_warnings(self) -> None:
        stage = PostprocessStage(_pipeline_config())
        ctx = PipelineContext(response={
            "request_id": "req-1",
            "session_id": "sess-1",
            "vlm_result": {
                "overlays": [],
                "model_version": "v2.1",
                "warnings": ["low light"],
            },
        })
        result = stage.execute(ctx)
        assert result.response["model_version"] == "v2.1"
        assert result.response["warnings"] == ["low light"]


# ---------------------------------------------------------------------------
# Snapshot pipeline (integration)
# ---------------------------------------------------------------------------

class TestSnapshotPipeline:
    def test_full_pipeline_returns_valid_response(self) -> None:
        backend = _vlm_backend()
        config = _pipeline_config()
        pipeline = build_snapshot_pipeline(backend, config)

        ctx = PipelineContext(response={
            "image_base64": _make_jpeg_b64(),
            "request_id": "req-e2e",
            "session_id": "sess-e2e",
        })
        result = pipeline.run(ctx, session_id="sess-e2e")

        payload = result.response
        assert payload is not None
        assert payload["request_id"] == "req-e2e"
        assert payload["session_id"] == "sess-e2e"
        assert "created_at" in payload
        assert len(payload["overlays"]) == 1
        assert payload["overlays"][0]["confidence"] == 0.95

    def test_per_stage_timeout_fires_408(self) -> None:
        class SlowStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                time.sleep(2)
                return context

        pipeline = SnapshotPipeline(
            stages=[("slow_stage", SlowStage(), 100)],
            total_timeout_ms=5000,
        )
        with pytest.raises(PipelineTimeoutError) as exc_info:
            pipeline.run(PipelineContext(), session_id="timeout-test")
        assert exc_info.value.status_code == 408

    def test_stage_error_propagates(self) -> None:
        class BrokenStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                raise RuntimeError("stage exploded")

        pipeline = SnapshotPipeline(
            stages=[("broken", BrokenStage(), 5000)],
            total_timeout_ms=5000,
        )
        with pytest.raises(RuntimeError, match="stage exploded"):
            pipeline.run(PipelineContext(), session_id="error-test")

    def test_timing_metadata_attached_when_enabled(self) -> None:
        backend = _vlm_backend()
        config = _pipeline_config()
        config["orchestrator"]["include_timing_metadata"] = True
        pipeline = build_snapshot_pipeline(backend, config)

        ctx = PipelineContext(response={
            "image_base64": _make_jpeg_b64(),
            "request_id": "req-t",
            "session_id": "sess-t",
        })
        result = pipeline.run(ctx, session_id="sess-t")
        assert "_timing" in result.response
        assert len(result.response["_timing"]["stages"]) == 4


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_phase_1_returns_snapshot_pipeline(self) -> None:
        backend = _vlm_backend()
        config = _pipeline_config()
        config["orchestrator"]["phase"] = 1
        pipeline = get_pipeline(backend, config)
        assert isinstance(pipeline, SnapshotPipeline)

    def test_phase_3_returns_snapshot_pipeline(self) -> None:
        backend = _vlm_backend()
        config = _pipeline_config()
        config["orchestrator"]["phase"] = 3
        pipeline = get_pipeline(backend, config)
        assert isinstance(pipeline, SnapshotPipeline)

    def test_phase_4_raises_not_implemented(self) -> None:
        backend = _vlm_backend()
        config = _pipeline_config()
        config["orchestrator"]["phase"] = 4
        with pytest.raises(NotImplementedError, match="phase 4"):
            get_pipeline(backend, config)
