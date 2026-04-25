import type { AnalysisRequest, HealthResponse, OverlayResponse } from "../types/overlay";

const REQUEST_TIMEOUT_MS = 5000;
const DEFAULT_HEADERS = { "Content-Type": "application/json" } as const;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() ?? "";

export type ApiErrorCode =
  | "BAD_REQUEST"
  | "RATE_LIMITED"
  | "REQUEST_TIMEOUT"
  | "SERVER_ERROR"
  | "NETWORK_ERROR"
  | "INVALID_RESPONSE"
  | "UNKNOWN_ERROR";

export class ApiClientError extends Error {
  readonly code: ApiErrorCode;
  readonly status?: number;
  readonly isTimeout: boolean;

  constructor(message: string, code: ApiErrorCode, status?: number, isTimeout = false) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.isTimeout = isTimeout;
  }
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isString = (value: unknown): value is string => typeof value === "string";
const isBoolean = (value: unknown): value is boolean => typeof value === "boolean";

const buildUrl = (path: string): string => {
  if (!API_BASE_URL) {
    return path;
  }
  const normalizedBase = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
};

const mapHttpError = (status: number): ApiClientError => {
  switch (status) {
    case 422:
      return new ApiClientError(
        "The snapshot payload is invalid. Please capture again and try once more.",
        "BAD_REQUEST",
        status,
      );
    case 429:
      return new ApiClientError(
        "Too many requests were sent in a short time. Please wait a moment and retry.",
        "RATE_LIMITED",
        status,
      );
    case 408:
      return new ApiClientError(
        "The server timed out processing this snapshot. Please try again.",
        "REQUEST_TIMEOUT",
        status,
      );
    default:
      if (status >= 500) {
        return new ApiClientError(
          "The analysis service is temporarily unavailable. Please try again shortly.",
          "SERVER_ERROR",
          status,
        );
      }
      return new ApiClientError("Unexpected API response. Please retry.", "UNKNOWN_ERROR", status);
  }
};

const validateOverlayResponse = (value: unknown): OverlayResponse => {
  if (!isObject(value)) {
    throw new ApiClientError("Analyze response is not an object.", "INVALID_RESPONSE");
  }

  const { request_id, session_id, created_at, overlays } = value;
  if (!isString(request_id) || !isString(session_id) || !isString(created_at) || !Array.isArray(overlays)) {
    throw new ApiClientError("Analyze response has an invalid top-level shape.", "INVALID_RESPONSE");
  }

  overlays.forEach((overlay, index) => {
    if (!isObject(overlay)) {
      throw new ApiClientError(`Overlay at index ${index} is invalid.`, "INVALID_RESPONSE");
    }
    const bbox = overlay.bbox;
    if (!isObject(bbox)) {
      throw new ApiClientError(`Overlay bbox at index ${index} is missing.`, "INVALID_RESPONSE");
    }
    if (
      !isNumber(bbox.x) ||
      !isNumber(bbox.y) ||
      !isNumber(bbox.width) ||
      !isNumber(bbox.height) ||
      !isString(overlay.label) ||
      !isNumber(overlay.confidence) ||
      !isString(overlay.ui_layer) ||
      !isString(overlay.overlay_type) ||
      !isBoolean(overlay.action_required)
    ) {
      throw new ApiClientError(`Overlay at index ${index} has invalid fields.`, "INVALID_RESPONSE");
    }
  });

  return value as unknown as OverlayResponse;
};

const validateHealthResponse = (value: unknown): HealthResponse => {
  if (!isObject(value) || !isString(value.status)) {
    throw new ApiClientError("Health response has an invalid shape.", "INVALID_RESPONSE");
  }
  return value as unknown as HealthResponse;
};

async function fetchJson(url: string, init: RequestInit): Promise<unknown> {
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        ...DEFAULT_HEADERS,
        ...(init.headers ?? {}),
      },
    });

    if (!response.ok) {
      throw mapHttpError(response.status);
    }

    return (await response.json()) as unknown;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError(
        "Request timed out after 5 seconds. Please try again.",
        "REQUEST_TIMEOUT",
        408,
        true,
      );
    }
    if (error instanceof Error) {
      throw new ApiClientError(
        "Unable to reach the analysis service. Check your connection and retry.",
        "NETWORK_ERROR",
      );
    }
    throw new ApiClientError("Unexpected networking failure.", "UNKNOWN_ERROR");
  } finally {
    window.clearTimeout(timeoutHandle);
  }
}

export async function postAnalyze(payload: AnalysisRequest): Promise<OverlayResponse> {
  const raw = await fetchJson(buildUrl("/analyze"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return validateOverlayResponse(raw);
}

export async function getHealth(): Promise<HealthResponse> {
  const raw = await fetchJson(buildUrl("/health"), {
    method: "GET",
  });
  return validateHealthResponse(raw);
}
