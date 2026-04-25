import { useCallback, useMemo, useRef, useState } from "react";

import { ApiClientError, postAnalyze } from "../services/api";
import type {
  AnalysisRequest,
  OverlayResponse,
  SnapshotAnalysisInput,
  SnapshotAudioPayload,
} from "../types/overlay";

type SnapshotStatus = "idle" | "loading" | "success" | "error";

export interface UseSnapshotAnalysisDependencies {
  captureFrame: () => Promise<string> | string;
  recordAudio?: () => Promise<SnapshotAudioPayload | undefined>;
}

export interface UseSnapshotAnalysisState {
  status: SnapshotStatus;
  isLoading: boolean;
  data: OverlayResponse | null;
  error: string | null;
  errorCode: ApiClientError["code"] | null;
}

export interface UseSnapshotAnalysisReturn extends UseSnapshotAnalysisState {
  runAnalysis: (input: Omit<SnapshotAnalysisInput, "imageBase64" | "audio">) => Promise<OverlayResponse>;
  reset: () => void;
}

const buildRequest = (
  input: SnapshotAnalysisInput,
  requestId: string,
  audio: SnapshotAudioPayload | undefined,
): AnalysisRequest => ({
  request_id: requestId,
  session_id: input.sessionId,
  image_base64: input.imageBase64,
  query: input.query,
  capture_ts_ms: input.captureTsMs ?? Date.now(),
  frame_size: input.frameSize,
  audio_base64: audio?.audioBase64,
  audio_format: audio?.audioFormat,
  client: {
    app_version: input.client?.appVersion,
    device_id: input.client?.deviceId,
    platform: input.client?.platform,
  },
});

const nextRequestId = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

export function useSnapshotAnalysis(
  dependencies: UseSnapshotAnalysisDependencies,
): UseSnapshotAnalysisReturn {
  const [status, setStatus] = useState<SnapshotStatus>("idle");
  const [data, setData] = useState<OverlayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<ApiClientError["code"] | null>(null);
  const activeRequestIdRef = useRef<string | null>(null);

  const reset = useCallback(() => {
    activeRequestIdRef.current = null;
    setStatus("idle");
    setData(null);
    setError(null);
    setErrorCode(null);
  }, []);

  const runAnalysis = useCallback(
    async (input: Omit<SnapshotAnalysisInput, "imageBase64" | "audio">): Promise<OverlayResponse> => {
      const requestId = nextRequestId();
      activeRequestIdRef.current = requestId;
      setStatus("loading");
      setError(null);
      setErrorCode(null);

      try {
        const imageBase64 = await Promise.resolve(dependencies.captureFrame());
        const audio = dependencies.recordAudio
          ? await dependencies.recordAudio()
          : undefined;

        const requestPayload = buildRequest(
          {
            ...input,
            imageBase64,
            audio,
          },
          requestId,
          audio,
        );

        const response = await postAnalyze(requestPayload);

        if (activeRequestIdRef.current !== requestId) {
          throw new ApiClientError("A newer analyze request superseded this result.", "UNKNOWN_ERROR");
        }

        setData(response);
        setStatus("success");
        return response;
      } catch (unknownError) {
        if (activeRequestIdRef.current !== requestId) {
          throw unknownError;
        }
        const normalizedError =
          unknownError instanceof ApiClientError
            ? unknownError
            : new ApiClientError("Snapshot analysis failed. Please try again.", "UNKNOWN_ERROR");

        setStatus("error");
        setData(null);
        setError(normalizedError.message);
        setErrorCode(normalizedError.code);
        throw normalizedError;
      }
    },
    [dependencies],
  );

  const value = useMemo<UseSnapshotAnalysisReturn>(
    () => ({
      status,
      isLoading: status === "loading",
      data,
      error,
      errorCode,
      runAnalysis,
      reset,
    }),
    [data, error, errorCode, reset, runAnalysis, status],
  );

  return value;
}
