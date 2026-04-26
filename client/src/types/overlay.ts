import type {
  AnalysisRequest as SharedAnalysisRequest,
  AudioFormat,
  BBox,
  Overlay,
  OverlayResponse as SharedOverlayResponse,
  OverlayType,
  UiLayer,
} from "../../../shared/schemas/types";

export type AnalysisRequest = SharedAnalysisRequest;
export type OverlayResponse = SharedOverlayResponse;
export type OverlayItem = Overlay;
export type BoundingBox = BBox;
export type { OverlayType, UiLayer };
export type SupportedAudioFormat = AudioFormat;

export interface HealthResponse {
  status: string;
  models?: Record<string, unknown>;
}

export interface SnapshotAudioPayload {
  audioBase64: string;
  audioFormat: SupportedAudioFormat;
}

export interface SnapshotAnalysisInput {
  query: string;
  sessionId: string;
  imageBase64: string;
  captureTsMs?: number;
  frameSize?: { width: number; height: number };
  client?: {
    appVersion?: string;
    deviceId?: string;
    platform?: string;
  };
  audio?: SnapshotAudioPayload;
}
