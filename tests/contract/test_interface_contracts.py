from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage
from shared.interfaces.tracker_base import TrackerBackend, TrackerState


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class NoOpInferenceBackend(InferenceBackend):
    def load(self) -> None:
        return None

    def warmup(self) -> None:
        return None

    def is_ready(self) -> bool:
        return True

    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        return {"image_len": len(image), "query": query}

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        return {"bbox": bbox, "bytes": len(image)}

    def estimate_depth(self, image: bytes) -> Any:
        return {"bytes": len(image)}

    def transcribe(self, audio: bytes) -> str:
        return f"audio:{len(audio)}"


class NoOpStage(PipelineStage):
    def execute(self, context: PipelineContext) -> PipelineContext:
        return context


class NoOpTracker(TrackerBackend):
    def __init__(self) -> None:
        self._state = TrackerState.IDLE
        self._mask: Any = None

    @property
    def state(self) -> TrackerState:
        return self._state

    def seed(self, mask: Any) -> None:
        self._mask = mask
        self._state = TrackerState.SEEDED

    def propagate(self, frame: bytes) -> Any:
        if self._mask is None:
            self._state = TrackerState.LOST
            return None
        self._state = TrackerState.TRACKING
        return {"frame_len": len(frame), "mask": self._mask}

    def reset(self) -> None:
        self._mask = None
        self._state = TrackerState.IDLE


def _contains_forbidden_imports(module_name: str) -> bool:
    module_path = PROJECT_ROOT / Path(*module_name.split("."))
    source = module_path.with_suffix(".py").read_text(encoding="utf-8")
    forbidden_prefixes = ("numpy", "torch", "cv2", "fastapi", "pydantic")
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            imported = stripped.replace("import ", "", 1).split(" as ")[0].split(",")[0].strip()
            if imported.startswith(forbidden_prefixes):
                return True
        if stripped.startswith("from "):
            imported = stripped.replace("from ", "", 1).split(" import ", 1)[0].strip()
            if imported.startswith(forbidden_prefixes):
                return True
    return False


def test_interface_modules_import_cleanly() -> None:
    modules = (
        "shared.interfaces.inference_base",
        "shared.interfaces.pipeline_stage",
        "shared.interfaces.tracker_base",
    )
    for module_name in modules:
        importlib.import_module(module_name)
        assert not _contains_forbidden_imports(module_name)


def test_noop_implementations_are_instantiable() -> None:
    inference = NoOpInferenceBackend()
    stage = NoOpStage()
    tracker = NoOpTracker()

    assert inference.is_ready() is True
    assert isinstance(stage.execute(PipelineContext(query="hello")), PipelineContext)
    assert tracker.state is TrackerState.IDLE


def test_pipeline_context_defaults_and_flow() -> None:
    context = PipelineContext(image=b"img", query="where", bbox=[0.1, 0.2, 0.3, 0.4])

    stage = NoOpStage()
    next_context = stage.execute(context)

    assert next_context.image == b"img"
    assert next_context.query == "where"
    assert next_context.bbox == [0.1, 0.2, 0.3, 0.4]
