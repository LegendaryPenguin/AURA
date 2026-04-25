/**
 * AUTO-GENERATED CONTRACT TYPES
 * Source of truth: shared/schemas/*.json
 * Regenerate from JSON Schemas when contracts change.
 */

export type OverlayType = "diagnostic" | "hazard" | "info" | "reference";

export type UiLayer = "background" | "midground" | "foreground" | "hud";

export type TrackerState = "inactive" | "initializing" | "tracking" | "lost";

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Overlay {
  bbox: BBox;
  label: string;
  confidence: number;
  ui_layer: UiLayer;
  overlay_type: OverlayType;
  action_required: boolean;
  mask_rle?: string;
  depth_value?: number;
  object_id?: string;
}

export interface OverlayResponse {
  request_id: string;
  session_id: string;
  created_at: string;
  model_version?: string;
  overlays: Overlay[];
  tracking_state?: TrackerState;
  warnings?: string[];
}

export type AudioFormat = "wav" | "webm" | "mp3" | "m4a";

export interface FrameSize {
  width: number;
  height: number;
}

export interface ClientInfo {
  app_version?: string;
  device_id?: string;
  platform?: string;
}

export interface AnalysisRequest {
  request_id: string;
  session_id: string;
  image_base64: string;
  query: string;
  capture_ts_ms: number;
  audio_base64?: string;
  audio_format?: AudioFormat;
  frame_size?: FrameSize;
  client?: ClientInfo;
}

export interface TrackedObject {
  object_id: string;
  label: string;
  bbox: BBox;
  confidence: number;
  last_seen_ms: number;
  depth_value?: number;
}

export interface TrackingState {
  session_id: string;
  state: TrackerState;
  tracked_objects: TrackedObject[];
  updated_at: string;
}

export type StreamFrameType =
  | "overlay_update"
  | "tracking_update"
  | "heartbeat"
  | "error";

export interface StreamTrackingStateRef {
  state: TrackerState;
  tracked_count: number;
}

export interface StreamErrorPayload {
  code: string;
  message: string;
}

export interface StreamFrame {
  session_id: string;
  frame_id: string;
  sent_at: string;
  frame_type: StreamFrameType;
  overlays: Overlay[];
  tracking_state?: StreamTrackingStateRef;
  error?: StreamErrorPayload;
}
