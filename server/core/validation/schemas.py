from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class OverlayType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    HAZARD = "hazard"
    INFO = "info"
    REFERENCE = "reference"


class UILayer(str, Enum):
    BACKGROUND = "background"
    MIDGROUND = "midground"
    FOREGROUND = "foreground"
    HUD = "hud"


class TrackingState(str, Enum):
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    TRACKING = "tracking"
    LOST = "lost"


class BBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)


class Overlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bbox: BBox
    label: NonEmptyString
    confidence: float = Field(ge=0.0, le=1.0)
    ui_layer: UILayer
    overlay_type: OverlayType
    action_required: bool
    mask_rle: NonEmptyString | None = None
    depth_value: float | None = None
    object_id: NonEmptyString | None = None


class OverlayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: NonEmptyString
    session_id: NonEmptyString
    created_at: NonEmptyString
    model_version: NonEmptyString | None = None
    overlays: list[Overlay]
    tracking_state: TrackingState | None = None
    warnings: list[NonEmptyString] | None = None
