from __future__ import annotations

import importlib
import json
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


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise AssertionError(f"Unsupported schema ref: {ref}")

    node: Any = schema
    for token in ref.removeprefix("#/").split("/"):
        node = node[token]

    if not isinstance(node, dict):
        raise AssertionError(f"Schema ref does not point to an object node: {ref}")
    return node


def _validate_schema_node(value: Any, node: dict[str, Any], root_schema: dict[str, Any], path: str) -> None:
    if "$ref" in node:
        _validate_schema_node(value, _resolve_ref(root_schema, node["$ref"]), root_schema, path)
        return

    expected_type = node.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise AssertionError(f"{path}: expected object")

        required_fields = node.get("required", [])
        for field_name in required_fields:
            if field_name not in value:
                raise AssertionError(f"{path}: missing required field '{field_name}'")

        properties = node.get("properties", {})
        if node.get("additionalProperties") is False:
            unknown = set(value.keys()) - set(properties.keys())
            if unknown:
                raise AssertionError(f"{path}: unexpected fields {sorted(unknown)}")

        for field_name, field_value in value.items():
            if field_name in properties:
                _validate_schema_node(
                    field_value,
                    properties[field_name],
                    root_schema,
                    f"{path}.{field_name}",
                )
        return

    if expected_type == "array":
        if not isinstance(value, list):
            raise AssertionError(f"{path}: expected array")
        item_schema = node.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema_node(item, item_schema, root_schema, f"{path}[{index}]")
        return

    if expected_type == "string":
        if not isinstance(value, str):
            raise AssertionError(f"{path}: expected string")
        min_length = node.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise AssertionError(f"{path}: string shorter than minLength {min_length}")
        enum_values = node.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            raise AssertionError(f"{path}: '{value}' not in enum {enum_values}")
        return

    if expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise AssertionError(f"{path}: expected number")
        minimum = node.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise AssertionError(f"{path}: {value} < minimum {minimum}")
        maximum = node.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise AssertionError(f"{path}: {value} > maximum {maximum}")
        exclusive_minimum = node.get("exclusiveMinimum")
        if isinstance(exclusive_minimum, (int, float)) and value <= exclusive_minimum:
            raise AssertionError(f"{path}: {value} <= exclusiveMinimum {exclusive_minimum}")
        return

    if expected_type == "boolean":
        if not isinstance(value, bool):
            raise AssertionError(f"{path}: expected boolean")
        return

    raise AssertionError(f"{path}: unsupported schema node type '{expected_type}'")


def test_golden_response_fixtures_match_overlay_response_schema() -> None:
    schema_path = PROJECT_ROOT / "shared/schemas/overlay_response.json"
    fixtures_dir = PROJECT_ROOT / "tests/fixtures/responses"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    assert fixture_paths, "No golden response fixtures found"

    for fixture_path in fixture_paths:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        _validate_schema_node(payload, schema, schema, fixture_path.name)
