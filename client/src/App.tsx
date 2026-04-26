import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AgentActionToast } from "./components/agents/AgentActionToast";
import OverlayCanvas from "./components/overlays/OverlayCanvas";
import { ConfidenceIndicator } from "./components/ui/ConfidenceIndicator";
import { DepthHeatmap } from "./components/ui/DepthHeatmap";
import { FallbackVideo } from "./components/ui/FallbackVideo";
import { ScanAnimation } from "./components/ui/ScanAnimation";
import { ScanReticle } from "./components/ui/ScanReticle";
import { useFallback } from "./hooks/useFallback";
import { useFrameCapture } from "./hooks/useFrameCapture";
import { useOverlay } from "./hooks/useOverlay";
import { useSnapshotAnalysis } from "./hooks/useSnapshotAnalysis";
import {
  ApiClientError,
  getHealth,
  getHealthForModel,
  getBackendTarget,
  getProcessingModel,
  setProcessingModel,
  type ProcessingModel,
} from "./services/api";
import type { OverlayType, UiLayer } from "../../shared/schemas/types";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

const PHASES = [0, 1, 2, 3, 4, 5] as const;
const phaseLabels: Record<number, string> = {
  0: "Fallback",
  1: "Snapshot",
  2: "Live Camera + Voice",
  3: "Auto-Scan",
  4: "Tracked AR",
  5: "Real-Time Streaming",
};

const LAYER_BY_INDEX: readonly UiLayer[] = ["background", "midground", "foreground", "hud"] as const;
const TYPE_BY_NAME: Record<string, OverlayType> = {
  diagnostic: "diagnostic",
  hazard: "hazard",
  info: "info",
  reference: "reference",
};
const PROCESSING_MODEL_OPTIONS: ReadonlyArray<{ value: ProcessingModel; label: string }> = [
  { value: "qwen3b", label: "Qwen 3B (local)" },
  { value: "qwen7b", label: "Qwen 7B config" },
  { value: "moondream2", label: "Moondream2" },
];

const phase0DemoOverlay = {
  bbox: { x: 0.22, y: 0.24, width: 0.32, height: 0.28 },
  label: "Demo object",
  confidence: 0.93,
  ui_layer: "midground" as const,
  overlay_type: "info" as const,
  action_required: false,
};

interface VideoSimCaptureCreateResponse {
  job_id: string;
  status: string;
  stage?: string;
  fast_preview?: boolean;
  status_url: string;
  video_url: string;
}

interface VideoSimJobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  stage?: "uploading" | "queued" | "analyzing" | "rendering" | "encoding" | "ready" | "error";
  message?: string;
  error?: string | null;
  video_url?: string;
  elapsed_seconds?: number;
  eta_seconds?: number | null;
  fast_preview?: boolean;
}

interface PaperLockRect {
  x: number;
  y: number;
  w: number;
  h: number;
  confidence: number;
}

interface GrayscaleFrame {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}

interface FeaturePoint {
  x: number;
  y: number;
}

interface FusedAnchorTransform {
  offsetX: number;
  offsetY: number;
  scale: number;
  tiltX: number;
  tiltY: number;
  visibility: number;
  initialPxX: number;
  initialPxY: number;
  initialWidthPct: number;
  ready: boolean;
}

interface ARAnchorData {
  rect: PaperLockRect;
  features: FeaturePoint[];
  reference: GrayscaleFrame;
  refWidth: number;
  refHeight: number;
  initialOrientation: { alpha: number; beta: number; gamma: number } | null;
}

function computeGrayscale(
  source: HTMLVideoElement | HTMLImageElement | null,
  targetWidth: number,
): GrayscaleFrame | null {
  if (!source) return null;
  const sourceWidth = source instanceof HTMLVideoElement ? source.videoWidth : source.naturalWidth;
  const sourceHeight = source instanceof HTMLVideoElement ? source.videoHeight : source.naturalHeight;
  if (!sourceWidth || !sourceHeight) return null;
  const w = Math.min(targetWidth, sourceWidth);
  const h = Math.max(1, Math.round(sourceHeight * (w / sourceWidth)));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(source, 0, 0, w, h);
  const rgba = ctx.getImageData(0, 0, w, h).data;
  const gray = new Uint8ClampedArray(w * h);
  for (let i = 0, j = 0; i < rgba.length; i += 4, j += 1) {
    gray[j] = ((rgba[i]! * 0.299 + rgba[i + 1]! * 0.587 + rgba[i + 2]! * 0.114) | 0);
  }
  return { width: w, height: h, data: gray };
}

function gradientMagnitude(gray: GrayscaleFrame, x: number, y: number): number {
  if (x <= 0 || y <= 0 || x >= gray.width - 1 || y >= gray.height - 1) return 0;
  const idx = y * gray.width + x;
  const ix = (gray.data[idx + 1]! - gray.data[idx - 1]!) * 0.5;
  const iy = (gray.data[idx + gray.width]! - gray.data[idx - gray.width]!) * 0.5;
  return Math.abs(ix) + Math.abs(iy);
}

function sampleFeaturePoints(gray: GrayscaleFrame, rect: PaperLockRect, gridX = 7, gridY = 6): FeaturePoint[] {
  const x0 = Math.max(3, Math.floor(rect.x * gray.width));
  const y0 = Math.max(3, Math.floor(rect.y * gray.height));
  const x1 = Math.min(gray.width - 4, Math.ceil((rect.x + rect.w) * gray.width));
  const y1 = Math.min(gray.height - 4, Math.ceil((rect.y + rect.h) * gray.height));
  if (x1 - x0 < 8 || y1 - y0 < 8) return [];
  const stepX = Math.max(1, Math.floor((x1 - x0) / gridX));
  const stepY = Math.max(1, Math.floor((y1 - y0) / gridY));
  const out: FeaturePoint[] = [];
  for (let cy = 0; cy < gridY; cy++) {
    for (let cx = 0; cx < gridX; cx++) {
      const cellLeft = x0 + cx * stepX;
      const cellTop = y0 + cy * stepY;
      const cellRight = Math.min(x1 - 1, cellLeft + stepX);
      const cellBottom = Math.min(y1 - 1, cellTop + stepY);
      let bestX = cellLeft + ((cellRight - cellLeft) >> 1);
      let bestY = cellTop + ((cellBottom - cellTop) >> 1);
      let bestScore = gradientMagnitude(gray, bestX, bestY);
      for (let py = cellTop; py < cellBottom; py += 2) {
        for (let px = cellLeft; px < cellRight; px += 2) {
          const score = gradientMagnitude(gray, px, py);
          if (score > bestScore) {
            bestScore = score;
            bestX = px;
            bestY = py;
          }
        }
      }
      if (bestScore > 6) {
        out.push({ x: bestX / gray.width, y: bestY / gray.height });
      }
    }
  }
  return out;
}

function lkTrackPoint(
  ref: GrayscaleFrame,
  cur: GrayscaleFrame,
  refX: number,
  refY: number,
  hintDx: number,
  hintDy: number,
): { dx: number; dy: number; residual: number } | null {
  const win = 3;
  const maxIters = 4;
  let dx = hintDx;
  let dy = hintDy;
  if (refX - win < 1 || refY - win < 1 || refX + win >= ref.width - 1 || refY + win >= ref.height - 1) {
    return null;
  }
  let lastResidual = 999;
  for (let iter = 0; iter < maxIters; iter++) {
    let gxx = 0;
    let gxy = 0;
    let gyy = 0;
    let gxt = 0;
    let gyt = 0;
    let absDt = 0;
    let count = 0;
    for (let py = -win; py <= win; py++) {
      for (let px = -win; px <= win; px++) {
        const xr = refX + px;
        const yr = refY + py;
        const xc = xr + dx;
        const yc = yr + dy;
        if (xc < 1 || yc < 1 || xc >= cur.width - 1 || yc >= cur.height - 1) continue;
        const xci = xc | 0;
        const yci = yc | 0;
        const refIdx = yr * ref.width + xr;
        const curIdx = yci * cur.width + xci;
        const ix = (ref.data[refIdx + 1]! - ref.data[refIdx - 1]!) * 0.5;
        const iy = (ref.data[refIdx + ref.width]! - ref.data[refIdx - ref.width]!) * 0.5;
        const it = cur.data[curIdx]! - ref.data[refIdx]!;
        gxx += ix * ix;
        gxy += ix * iy;
        gyy += iy * iy;
        gxt += ix * it;
        gyt += iy * it;
        absDt += it >= 0 ? it : -it;
        count += 1;
      }
    }
    if (count === 0) return null;
    const det = gxx * gyy - gxy * gxy;
    if (Math.abs(det) < 1e-3) return null;
    const ux = (-gyy * gxt + gxy * gyt) / det;
    const uy = (gxy * gxt - gxx * gyt) / det;
    dx += ux;
    dy += uy;
    lastResidual = absDt / count;
    if (Math.abs(ux) + Math.abs(uy) < 0.05) break;
  }
  return { dx, dy, residual: lastResidual };
}

function resolveApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const alreadyApiPrefixed = normalized.startsWith("/api/");
  const isVideoSim = normalized.includes("/video-sim/");
  if (isVideoSim) {
    return alreadyApiPrefixed ? normalized : `/api${normalized}`;
  }
  const target = getBackendTarget().baseUrl;
  if (!target) {
    return alreadyApiPrefixed ? normalized : `/api${normalized}`;
  }
  return `${target}${normalized}`;
}

function PhoneCaptureApp() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [capturedFrameUrl, setCapturedFrameUrl] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");
  const [status, setStatus] = useState<VideoSimJobStatusResponse["status"] | "idle">("idle");
  const [stage, setStage] = useState<VideoSimJobStatusResponse["stage"] | "idle">("idle");
  const [statusMessage, setStatusMessage] = useState<string>("Point camera at your equation and tap capture.");
  const [videoUrl, setVideoUrl] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [cameraReady, setCameraReady] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string>("");
  const [captureFlash, setCaptureFlash] = useState<boolean>(false);
  const [showOverlayVideo, setShowOverlayVideo] = useState<boolean>(false);
  const [fastPreview, setFastPreview] = useState<boolean>(true);
  const [trackingReady, setTrackingReady] = useState<boolean>(false);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const overlayVideoRef = useRef<HTMLVideoElement | null>(null);
  const overlaySectionRef = useRef<HTMLElement | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const anchorRef = useRef<ARAnchorData | null>(null);
  const fusedTransformRef = useRef<FusedAnchorTransform>({
    offsetX: 0,
    offsetY: 0,
    scale: 1,
    tiltX: 0,
    tiltY: 0,
    visibility: 0,
    initialPxX: 0.5,
    initialPxY: 0.5,
    initialWidthPct: 60,
    ready: false,
  });
  const lastFlowOffsetRef = useRef<{ dx: number; dy: number; scale: number; inlierRatio: number } | null>(null);
  const trackedHintsRef = useRef<Array<{ dx: number; dy: number }>>([]);
  const orientationAnchorRef = useRef<{ alpha: number; beta: number; gamma: number } | null>(null);
  const orientationCurrentRef = useRef<{ alpha: number; beta: number; gamma: number } | null>(null);
  const orientationListenerRef = useRef<((event: DeviceOrientationEvent) => void) | null>(null);
  const lastTrackingConfRef = useRef<number>(0);
  const lowConfSinceRef = useRef<number>(0);
  const reacquireRef = useRef<boolean>(false);

  const statusStory = useMemo(() => {
    if (stage === "uploading") return "Uploading captured frame...";
    if (stage === "queued") return "Queued...";
    if (stage === "analyzing") return "Analyzing paper geometry...";
    if (stage === "rendering") return "Composing AR tutorial...";
    if (stage === "encoding") return "Encoding video...";
    if (stage === "ready") return "AR tutorial ready.";
    if (status === "queued") return "Queued...";
    if (status === "running") return "Composing AR tutorial...";
    if (status === "done") return "AR tutorial ready.";
    if (status === "error") return statusMessage || "Generation failed.";
    return statusMessage;
  }, [stage, status, statusMessage]);

  const detectPaperRect = useCallback((source: HTMLVideoElement | HTMLImageElement | null): PaperLockRect | null => {
    if (!source) return null;
    const width = source instanceof HTMLVideoElement ? source.videoWidth : source.naturalWidth;
    const height = source instanceof HTMLVideoElement ? source.videoHeight : source.naturalHeight;
    if (!width || !height) return null;
    const sampleW = 220;
    const sampleH = Math.max(120, Math.round((sampleW * height) / width));
    const canvas = document.createElement("canvas");
    canvas.width = sampleW;
    canvas.height = sampleH;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(source, 0, 0, sampleW, sampleH);
    const imageData = ctx.getImageData(0, 0, sampleW, sampleH).data;

    let minX = sampleW;
    let minY = sampleH;
    let maxX = 0;
    let maxY = 0;
    let hitCount = 0;
    for (let y = 0; y < sampleH; y += 2) {
      for (let x = 0; x < sampleW; x += 2) {
        const idx = (y * sampleW + x) * 4;
        const r = imageData[idx]!;
        const g = imageData[idx + 1]!;
        const b = imageData[idx + 2]!;
        const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        const sat = Math.max(r, g, b) - Math.min(r, g, b);
        if (luminance > 140 && sat < 36) {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
          hitCount += 1;
        }
      }
    }
    if (hitCount < 120 || maxX <= minX || maxY <= minY) return null;
    const rectW = (maxX - minX) / sampleW;
    const rectH = (maxY - minY) / sampleH;
    const area = rectW * rectH;
    if (area < 0.08 || area > 0.9) return null;
    return {
      x: minX / sampleW,
      y: minY / sampleH,
      w: rectW,
      h: rectH,
      confidence: Math.min(1, hitCount / 900),
    };
  }, []);

  useEffect(() => {
    return () => {
      if (orientationListenerRef.current) {
        window.removeEventListener("deviceorientation", orientationListenerRef.current, true);
        orientationListenerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!jobId || status === "done" || status === "error" || status === "idle") {
      return;
    }
    const interval = window.setInterval(() => {
      void (async () => {
        try {
          const response = await fetch(resolveApiUrl(`/video-sim/jobs/${jobId}`));
          if (!response.ok) {
            throw new Error(`status polling failed (${response.status})`);
          }
          const payload = (await response.json()) as VideoSimJobStatusResponse;
          setStatus(payload.status);
          setStage(payload.stage ?? (payload.status === "done" ? "ready" : payload.status === "error" ? "error" : "rendering"));
          const elapsed = typeof payload.elapsed_seconds === "number" ? ` (${payload.elapsed_seconds}s)` : "";
          const eta = typeof payload.eta_seconds === "number" && payload.eta_seconds > 0 ? ` · ~${payload.eta_seconds}s left` : "";
          setStatusMessage(`${payload.message || payload.status}${elapsed}${eta}`);
          if (payload.status === "done") {
            const resolvedVideoUrl = resolveApiUrl(payload.video_url || `/video-sim/video/${jobId}`);
            setVideoUrl(resolvedVideoUrl);
            setShowOverlayVideo(true);
            window.clearInterval(interval);
          } else if (payload.status === "error") {
            setStatusMessage(payload.error || payload.message || "Video generation failed.");
            window.clearInterval(interval);
          }
        } catch (err) {
          const isAbort = err instanceof DOMException && err.name === "AbortError";
          if (isAbort) {
            setStatusMessage("Connection paused, retrying status...");
            return;
          }
          const transient = err instanceof TypeError;
          if (transient) {
            setStatusMessage("Network blip, retrying status...");
            return;
          }
          setStatus("error");
          setStage("error");
          setStatusMessage(err instanceof Error ? err.message : "Polling failed.");
          window.clearInterval(interval);
        }
      })();
    }, 1500);
    return () => window.clearInterval(interval);
  }, [jobId, status]);

  useEffect(() => {
    void startCamera();
    return () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop());
        cameraStreamRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!showOverlayVideo || !overlayVideoRef.current) {
      return;
    }
    overlayVideoRef.current.currentTime = 0;
    void overlayVideoRef.current.play().catch(() => undefined);
  }, [showOverlayVideo, videoUrl]);

  useEffect(() => {
    if (!trackingReady) {
      return;
    }
    let raf = 0;
    let running = true;
    let lastFlowAt = 0;
    const flowIntervalMs = 70;
    const pctPerDeg = 1 / 65;

    const accum = {
      offsetX: 0,
      offsetY: 0,
      scale: 1,
      tiltX: 0,
      tiltY: 0,
      visibility: 0,
    };

    const applyToDom = () => {
      const node = overlaySectionRef.current;
      const t = fusedTransformRef.current;
      if (!node || !t.ready) return;
      const cx = (t.initialPxX + t.offsetX) * 100;
      const cy = (t.initialPxY + t.offsetY) * 100;
      const widthPct = Math.min(96, Math.max(28, t.initialWidthPct * t.scale));
      node.style.left = `${cx}%`;
      node.style.top = `${cy}%`;
      node.style.width = `${widthPct}vw`;
      node.style.transform = `translate(-50%, -50%) perspective(1100px) rotateX(${t.tiltX}deg) rotateY(${t.tiltY}deg)`;
      const v = Math.max(0, Math.min(1, t.visibility));
      node.style.opacity = `${v}`;
      node.style.visibility = v < 0.04 ? "hidden" : "visible";
      node.style.pointerEvents = v < 0.2 ? "none" : "auto";
    };

    const tick = (now: number) => {
      if (!running) return;
      const anchor = anchorRef.current;
      if (!anchor) {
        raf = window.requestAnimationFrame(tick);
        return;
      }

      let flowDxPct = lastFlowOffsetRef.current?.dx ?? 0;
      let flowDyPct = lastFlowOffsetRef.current?.dy ?? 0;
      let flowScale = lastFlowOffsetRef.current?.scale ?? 1;
      let flowInlierRatio = lastFlowOffsetRef.current?.inlierRatio ?? 0;

      if (now - lastFlowAt >= flowIntervalMs && cameraVideoRef.current) {
        lastFlowAt = now;
        const cur = computeGrayscale(cameraVideoRef.current, anchor.reference.width);
        if (cur && cur.width === anchor.reference.width && cur.height === anchor.reference.height) {
          const features = anchor.features;
          const hints = trackedHintsRef.current;
          const refDxs: number[] = [];
          const refDys: number[] = [];
          let inliers = 0;
          for (let i = 0; i < features.length; i++) {
            const fp = features[i]!;
            const refX = (fp.x * anchor.reference.width) | 0;
            const refY = (fp.y * anchor.reference.height) | 0;
            const hint = hints[i] ?? { dx: 0, dy: 0 };
            const result = lkTrackPoint(anchor.reference, cur, refX, refY, hint.dx, hint.dy);
            if (result && result.residual < 22 && Math.hypot(result.dx, result.dy) < anchor.reference.width * 0.6) {
              refDxs.push(result.dx);
              refDys.push(result.dy);
              hints[i] = { dx: result.dx, dy: result.dy };
              inliers += 1;
            } else {
              hints[i] = { dx: hint.dx * 0.4, dy: hint.dy * 0.4 };
              refDxs.push(NaN);
              refDys.push(NaN);
            }
          }
          trackedHintsRef.current = hints;

          flowInlierRatio = inliers / Math.max(1, features.length);

          if (inliers >= 6) {
            const validDx = refDxs.filter((v) => !Number.isNaN(v)).sort((a, b) => a - b);
            const validDy = refDys.filter((v) => !Number.isNaN(v)).sort((a, b) => a - b);
            const medDx = validDx[Math.floor(validDx.length / 2)]!;
            const medDy = validDy[Math.floor(validDy.length / 2)]!;

            let centroidRefX = 0;
            let centroidRefY = 0;
            let centroidNowX = 0;
            let centroidNowY = 0;
            const validPairs: Array<{ rx: number; ry: number; nx: number; ny: number }> = [];
            for (let i = 0; i < features.length; i++) {
              if (Number.isNaN(refDxs[i]!)) continue;
              const fp = features[i]!;
              const rx = fp.x * anchor.reference.width;
              const ry = fp.y * anchor.reference.height;
              const nx = rx + refDxs[i]!;
              const ny = ry + refDys[i]!;
              centroidRefX += rx;
              centroidRefY += ry;
              centroidNowX += nx;
              centroidNowY += ny;
              validPairs.push({ rx, ry, nx, ny });
            }
            centroidRefX /= validPairs.length;
            centroidRefY /= validPairs.length;
            centroidNowX /= validPairs.length;
            centroidNowY /= validPairs.length;
            let spreadRef = 0;
            let spreadNow = 0;
            for (const p of validPairs) {
              spreadRef += Math.hypot(p.rx - centroidRefX, p.ry - centroidRefY);
              spreadNow += Math.hypot(p.nx - centroidNowX, p.ny - centroidNowY);
            }
            if (spreadRef > 1) {
              flowScale = Math.max(0.45, Math.min(2.4, spreadNow / spreadRef));
            }
            flowDxPct = medDx / anchor.reference.width;
            flowDyPct = medDy / anchor.reference.height;
          }

          lastFlowOffsetRef.current = {
            dx: flowDxPct,
            dy: flowDyPct,
            scale: flowScale,
            inlierRatio: flowInlierRatio,
          };
        }
      }

      const ori = orientationCurrentRef.current;
      const oriAnchor = orientationAnchorRef.current;
      let gyroDxPct = 0;
      let gyroDyPct = 0;
      let gyroTiltX = 0;
      let gyroTiltY = 0;
      let gyroAvailable = false;
      if (ori && oriAnchor) {
        gyroAvailable = true;
        let dAlpha = (ori.alpha ?? 0) - (oriAnchor.alpha ?? 0);
        while (dAlpha > 180) dAlpha -= 360;
        while (dAlpha < -180) dAlpha += 360;
        let dBeta = (ori.beta ?? 0) - (oriAnchor.beta ?? 0);
        while (dBeta > 180) dBeta -= 360;
        while (dBeta < -180) dBeta += 360;
        let dGamma = (ori.gamma ?? 0) - (oriAnchor.gamma ?? 0);
        while (dGamma > 180) dGamma -= 360;
        while (dGamma < -180) dGamma += 360;
        gyroDxPct = -dAlpha * pctPerDeg;
        gyroDyPct = dBeta * pctPerDeg;
        gyroTiltX = Math.max(-7, Math.min(7, dBeta * 0.35));
        gyroTiltY = Math.max(-7, Math.min(7, dGamma * 0.35));
      }

      let fusedDx: number;
      let fusedDy: number;
      let fusedScale = flowScale;
      const flowTrustworthy = flowInlierRatio >= 0.22;
      if (gyroAvailable && flowTrustworthy) {
        const flowAlpha = Math.min(0.35, flowInlierRatio * 0.45);
        fusedDx = (1 - flowAlpha) * gyroDxPct + flowAlpha * flowDxPct;
        fusedDy = (1 - flowAlpha) * gyroDyPct + flowAlpha * flowDyPct;
      } else if (gyroAvailable) {
        fusedDx = gyroDxPct;
        fusedDy = gyroDyPct;
        fusedScale = 1;
      } else if (flowTrustworthy) {
        fusedDx = flowDxPct;
        fusedDy = flowDyPct;
      } else {
        fusedDx = accum.offsetX;
        fusedDy = accum.offsetY;
        fusedScale = 1;
      }

      const trackingConfidence =
        gyroAvailable && flowTrustworthy
          ? Math.min(1, 0.6 + flowInlierRatio * 0.4)
          : gyroAvailable
            ? 0.55
            : flowTrustworthy
              ? Math.min(1, 0.4 + flowInlierRatio * 0.6)
              : 0;

      lastTrackingConfRef.current = trackingConfidence;
      if (trackingConfidence < 0.35) {
        if (lowConfSinceRef.current === 0) lowConfSinceRef.current = now;
        if (now - lowConfSinceRef.current > 600) {
          reacquireRef.current = true;
        }
      } else {
        lowConfSinceRef.current = 0;
        reacquireRef.current = false;
      }

      accum.offsetX = accum.offsetX * 0.72 + fusedDx * 0.28;
      accum.offsetY = accum.offsetY * 0.72 + fusedDy * 0.28;
      accum.scale = accum.scale * 0.86 + fusedScale * 0.14;
      accum.tiltX = accum.tiltX * 0.85 + gyroTiltX * 0.15;
      accum.tiltY = accum.tiltY * 0.85 + gyroTiltY * 0.15;

      const cxPct = anchor.rect.x + anchor.rect.w / 2 + accum.offsetX;
      const cyPct = anchor.rect.y + anchor.rect.h / 2 + accum.offsetY;
      const soft = 0.08;
      let geomVisibility = 1;
      if (cxPct < 0) geomVisibility = 0;
      else if (cxPct < soft) geomVisibility = cxPct / soft;
      else if (cxPct > 1) geomVisibility = 0;
      else if (cxPct > 1 - soft) geomVisibility = (1 - cxPct) / soft;
      if (cyPct < 0) geomVisibility = 0;
      else if (cyPct < soft) geomVisibility = Math.min(geomVisibility, cyPct / soft);
      else if (cyPct > 1) geomVisibility = 0;
      else if (cyPct > 1 - soft) geomVisibility = Math.min(geomVisibility, (1 - cyPct) / soft);

      const reacquireVisibility = reacquireRef.current ? 0 : 1;
      const targetVisibility = geomVisibility * reacquireVisibility;
      accum.visibility = accum.visibility * 0.78 + targetVisibility * 0.22;

      const prev = fusedTransformRef.current;
      fusedTransformRef.current = {
        offsetX: accum.offsetX,
        offsetY: accum.offsetY,
        scale: accum.scale,
        tiltX: accum.tiltX,
        tiltY: accum.tiltY,
        visibility: accum.visibility,
        initialPxX: prev.initialPxX,
        initialPxY: prev.initialPxY,
        initialWidthPct: prev.initialWidthPct,
        ready: prev.ready,
      };
      applyToDom();

      raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    return () => {
      running = false;
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [trackingReady]);

  const startCamera = async () => {
    try {
      setCameraError("");
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop());
        cameraStreamRef.current = null;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      cameraStreamRef.current = stream;
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream;
        await cameraVideoRef.current.play();
      }
      setCameraReady(true);
    } catch (err) {
      setCameraReady(false);
      setCameraError(err instanceof Error ? err.message : "Unable to access camera.");
    }
  };

  const lockAnchor = useCallback((): boolean => {
    const video = cameraVideoRef.current;
    if (!video) return false;
    const reference = computeGrayscale(video, 200);
    if (!reference) return false;
    const detected = detectPaperRect(video);
    const fallbackRect: PaperLockRect = { x: 0.18, y: 0.22, w: 0.64, h: 0.52, confidence: 0.5 };
    const rect = detected && detected.confidence >= 0.18 ? detected : fallbackRect;
    let features = sampleFeaturePoints(reference, rect, 7, 6);
    let usedRect = rect;
    if (features.length < 8) {
      const expanded: PaperLockRect = { x: 0.1, y: 0.15, w: 0.8, h: 0.7, confidence: 0.3 };
      const wider = sampleFeaturePoints(reference, expanded, 8, 7);
      if (wider.length < 8) return false;
      features = wider;
      usedRect = expanded;
    }
    anchorRef.current = {
      rect: usedRect,
      features,
      reference,
      refWidth: reference.width,
      refHeight: reference.height,
      initialOrientation: orientationCurrentRef.current
        ? { ...orientationCurrentRef.current }
        : null,
    };
    if (orientationCurrentRef.current) {
      orientationAnchorRef.current = { ...orientationCurrentRef.current };
    } else {
      orientationAnchorRef.current = null;
    }
    trackedHintsRef.current = features.map(() => ({ dx: 0, dy: 0 }));
    lastFlowOffsetRef.current = { dx: 0, dy: 0, scale: 1, inlierRatio: 1 };
    lastTrackingConfRef.current = 1;
    lowConfSinceRef.current = 0;
    reacquireRef.current = false;
    fusedTransformRef.current = {
      offsetX: 0,
      offsetY: 0,
      scale: 1,
      tiltX: 0,
      tiltY: 0,
      visibility: 1,
      initialPxX: usedRect.x + usedRect.w / 2,
      initialPxY: usedRect.y + usedRect.h / 2,
      initialWidthPct: Math.min(86, Math.max(46, usedRect.w * 110)),
      ready: true,
    };
    setTrackingReady(true);
    return true;
  }, [detectPaperRect]);

  const ensureOrientationListener = useCallback(async (): Promise<void> => {
    if (orientationListenerRef.current) return;
    type OrientationCtor = typeof DeviceOrientationEvent & {
      requestPermission?: () => Promise<"granted" | "denied">;
    };
    const ctor =
      typeof DeviceOrientationEvent !== "undefined"
        ? (DeviceOrientationEvent as unknown as OrientationCtor)
        : null;
    if (ctor && typeof ctor.requestPermission === "function") {
      try {
        const result = await ctor.requestPermission();
        if (result !== "granted") return;
      } catch {
        return;
      }
    }
    const handler = (event: DeviceOrientationEvent) => {
      orientationCurrentRef.current = {
        alpha: typeof event.alpha === "number" ? event.alpha : 0,
        beta: typeof event.beta === "number" ? event.beta : 0,
        gamma: typeof event.gamma === "number" ? event.gamma : 0,
      };
      if (!orientationAnchorRef.current && anchorRef.current) {
        orientationAnchorRef.current = { ...orientationCurrentRef.current };
      }
    };
    window.addEventListener("deviceorientation", handler, true);
    orientationListenerRef.current = handler;
  }, []);

  const captureFromCamera = async (): Promise<File | null> => {
    const video = cameraVideoRef.current;
    if (!video || video.videoWidth <= 0 || video.videoHeight <= 0) {
      setCameraError("Camera is not ready yet.");
      return null;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setCameraError("Canvas unavailable for capture.");
      return null;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob) {
      setCameraError("Could not capture image.");
      return null;
    }
    const capturedFile = new File([blob], `camera-capture-${Date.now()}.jpg`, { type: "image/jpeg" });
    setSelectedFile(capturedFile);
    setVideoUrl("");
    setJobId("");
    setStatus("idle");
    setStage("idle");
    setStatusMessage("Captured. Locking AR anchor...");
    setShowOverlayVideo(false);
    setCaptureFlash(true);
    window.setTimeout(() => setCaptureFlash(false), 180);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    setCapturedFrameUrl(dataUrl);
    const locked = lockAnchor();
    if (!locked) {
      setStatusMessage("Captured. Hold steady while we generate...");
    } else {
      setStatusMessage("Anchor locked. Composing AR tutorial...");
    }
    return capturedFile;
  };

  const onGenerate = async (fileOverride?: File) => {
    const sourceFile = fileOverride ?? selectedFile;
    if (!sourceFile) {
      setStatus("error");
      setStatusMessage("Please capture a photo first.");
      return;
    }
    setIsSubmitting(true);
    setStatus("queued");
    setStage("uploading");
    setStatusMessage("Uploading captured frame...");
    setVideoUrl("");
    setShowOverlayVideo(false);
    try {
      const form = new FormData();
      form.append("image", sourceFile, sourceFile.name || "capture.jpg");
      form.append("fast_preview", fastPreview ? "1" : "0");
      const response = await fetch(resolveApiUrl("/video-sim/capture"), {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Upload failed (${response.status}): ${text}`);
      }
      const payload = (await response.json()) as VideoSimCaptureCreateResponse;
      setJobId(payload.job_id);
      setStatus("running");
      setStage((payload.stage as VideoSimJobStatusResponse["stage"]) || "queued");
      setStatusMessage("Composing AR tutorial...");
    } catch (err) {
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      const isTransient = err instanceof TypeError;
      if (isAbort) {
        setStatus("error");
        setStage("error");
        setStatusMessage("Upload was interrupted. Tap Retake and try again.");
      } else if (isTransient) {
        setStatus("error");
        setStage("error");
        setStatusMessage("Network blip during upload. Tap Retake to retry.");
      } else {
        setStatus("error");
        setStage("error");
        setStatusMessage(err instanceof Error ? err.message : "Request failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const onPrimaryCapture = async () => {
    if (!cameraReady || isSubmitting) {
      return;
    }
    await ensureOrientationListener();
    const file = await captureFromCamera();
    if (!file) {
      return;
    }
    await onGenerate(file);
  };

  const onRetake = async () => {
    setJobId("");
    setStatus("idle");
    setStage("idle");
    setStatusMessage("Point camera at your equation and tap capture.");
    setShowOverlayVideo(false);
    setVideoUrl("");
    setCapturedFrameUrl("");
    anchorRef.current = null;
    orientationAnchorRef.current = null;
    lastFlowOffsetRef.current = null;
    trackedHintsRef.current = [];
    lastTrackingConfRef.current = 0;
    lowConfSinceRef.current = 0;
    reacquireRef.current = false;
    fusedTransformRef.current = {
      offsetX: 0,
      offsetY: 0,
      scale: 1,
      tiltX: 0,
      tiltY: 0,
      visibility: 0,
      initialPxX: 0.5,
      initialPxY: 0.5,
      initialWidthPct: 60,
      ready: false,
    };
    setTrackingReady(false);
    await startCamera();
  };

  const overlayInitialPlacement = useMemo(() => {
    if (!trackingReady) {
      return {
        left: "50%",
        top: "52%",
        width: "min(78vw, 640px)",
        transform: "translate(-50%, -50%)",
        anchored: false,
      };
    }
    const t = fusedTransformRef.current;
    return {
      left: `${t.initialPxX * 100}%`,
      top: `${t.initialPxY * 100}%`,
      width: `${Math.min(96, Math.max(28, t.initialWidthPct))}vw`,
      transform: "translate(-50%, -50%) perspective(1100px) rotateX(0deg) rotateY(0deg)",
      anchored: true,
    };
  }, [trackingReady]);

  const stageOrder: Array<NonNullable<VideoSimJobStatusResponse["stage"]>> = [
    "uploading",
    "queued",
    "analyzing",
    "rendering",
    "encoding",
    "ready",
  ];

  return (
    <main style={phoneStyles.arApp}>
      <video autoPlay muted playsInline ref={cameraVideoRef} style={phoneStyles.backgroundCamera} />
      {captureFlash ? <div style={phoneStyles.captureFlash} /> : null}

      <div style={phoneStyles.topHud}>
        <div style={phoneStyles.titleWrap}>
          <h1 style={phoneStyles.arTitle}>AURA AR Tutor</h1>
          <p style={phoneStyles.arSubtitle}>{statusStory}</p>
          <div style={phoneStyles.stageRow}>
            {stageOrder.map((step) => {
              const isActive = stage === step;
              const isDone = stageOrder.indexOf(step) < stageOrder.indexOf((stage as NonNullable<VideoSimJobStatusResponse["stage"]>) || "uploading");
              return (
                <span
                  key={step}
                  style={{
                    ...phoneStyles.stagePill,
                    ...(isDone ? phoneStyles.stagePillDone : null),
                    ...(isActive ? phoneStyles.stagePillActive : null),
                  }}
                >
                  {step}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {showOverlayVideo && videoUrl ? (
        <section
          ref={overlaySectionRef}
          style={{
            ...phoneStyles.overlayCard,
            left: overlayInitialPlacement.left,
            top: overlayInitialPlacement.top,
            width: overlayInitialPlacement.width,
            transform: overlayInitialPlacement.transform,
            opacity: 1,
            transition: overlayInitialPlacement.anchored
              ? "opacity 140ms ease, box-shadow 220ms ease"
              : phoneStyles.overlayCard.transition,
            willChange: "transform, opacity",
          }}
        >
          <video
            controls
            playsInline
            ref={overlayVideoRef}
            src={videoUrl}
            style={phoneStyles.overlayVideo}
            onError={() => setStatusMessage("Video failed to load. Tap Replay or Retake.")}
          />
          <div style={phoneStyles.resultControls}>
            <button onClick={() => void onRetake()} style={phoneStyles.resultButton} type="button">
              Retake
            </button>
            <button
              onClick={() => {
                if (overlayVideoRef.current) {
                  overlayVideoRef.current.currentTime = 0;
                  void overlayVideoRef.current.play().catch(() => undefined);
                }
              }}
              style={phoneStyles.resultButton}
              type="button"
            >
              Replay
            </button>
            <a download href={videoUrl} style={phoneStyles.resultLink}>
              Download
            </a>
          </div>
        </section>
      ) : null}

      <button
        disabled={!cameraReady || isSubmitting}
        onClick={() => void onPrimaryCapture()}
        style={phoneStyles.captureCta}
        type="button"
      >
        {isSubmitting ? "Generating..." : "Capture Image"}
      </button>

      <div style={phoneStyles.fallbackRow}>
        <label style={phoneStyles.fallbackToggle}>
          <input
            checked={fastPreview}
            onChange={(event) => setFastPreview(event.target.checked)}
            type="checkbox"
          />
          <span>Fast mode</span>
        </label>
      </div>
      {!showOverlayVideo && capturedFrameUrl ? <img alt="capture freeze" src={capturedFrameUrl} style={phoneStyles.freezePreview} /> : null}
      {cameraError ? <p style={phoneStyles.cameraError}>{cameraError}</p> : null}
    </main>
  );
}

function MainAuraApp() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const activeStreamRef = useRef<MediaStream | null>(null);
  const lastCaptureDataUrlRef = useRef<string | null>(null);
  const [phaseMode, setPhaseMode] = useState<number>(1);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAgentToast, setShowAgentToast] = useState(false);
  const [installPromptEvent, setInstallPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [showLogsView, setShowLogsView] = useState(false);
  const [frontendLogs, setFrontendLogs] = useState<string[]>([]);
  const [lastCaptureDataUrl, setLastCaptureDataUrl] = useState<string | null>(null);
  const [lastOverlayPreviewDataUrl, setLastOverlayPreviewDataUrl] = useState<string | null>(null);
  const [lastResponseJson, setLastResponseJson] = useState<string>("");
  const [backendHealthJson, setBackendHealthJson] = useState<string>("");
  const [processingModel, setProcessingModelState] = useState<ProcessingModel>(getProcessingModel());
  const [multiPhotoCount, setMultiPhotoCount] = useState<number>(3);
  const burstQueueRef = useRef<string[]>([]);

  const { captureFrame, captureBurst } = useFrameCapture();
  const {
    overlays,
    clearOverlays,
    hydrateFromResponse,
    replaceOverlays,
  } = useOverlay({ autoDismissMs: 0 });
  const { fallbackData, isFallbackActive, clearFallback } = useFallback();

  const captureForApi = useCallback(() => {
    const queued = burstQueueRef.current.shift();
    if (queued) {
      return queued;
    }
    const result = captureFrame(videoRef.current);
    if (!result) {
      throw new ApiClientError("Could not read a frame from the camera.", "INVALID_RESPONSE");
    }
    lastCaptureDataUrlRef.current = result.dataUrl;
    setLastCaptureDataUrl(result.dataUrl);
    const b64 = result.dataUrl.includes(",") ? (result.dataUrl.split(",")[1] ?? result.dataUrl) : result.dataUrl;
    return b64;
  }, [captureFrame]);

  const snapshot = useSnapshotAnalysis({ captureFrame: captureForApi });
  const backendTarget = useMemo(
    () => getBackendTarget(),
    [processingModel],
  );

  const modeName = useMemo(() => phaseLabels[phaseMode] ?? "Unknown", [phaseMode]);

  const pushLog = useCallback((entry: string) => {
    setFrontendLogs((prev) => [`${new Date().toLocaleTimeString()} ${entry}`, ...prev].slice(0, 80));
  }, []);

  const buildOverlayPreview = useCallback(
    async (captureDataUrl: string, overlayItems: Array<{ bbox: { x: number; y: number; width: number; height: number }; label: string }>) => {
      const image = new Image();
      image.src = captureDataUrl;
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve();
        image.onerror = () => reject(new Error("Failed to load capture image for overlay preview."));
      });

      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth || image.width || 1280;
      canvas.height = image.naturalHeight || image.height || 720;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        throw new Error("2D canvas context unavailable.");
      }
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

      ctx.lineWidth = 4;
      ctx.strokeStyle = "#22d3ee";
      ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      ctx.font = "16px Inter, system-ui, sans-serif";

      overlayItems.forEach((item) => {
        const x = item.bbox.x * canvas.width;
        const y = item.bbox.y * canvas.height;
        const w = item.bbox.width * canvas.width;
        const h = item.bbox.height * canvas.height;
        ctx.strokeRect(x, y, w, h);
        const label = item.label || "overlay";
        const metrics = ctx.measureText(label);
        const labelHeight = 22;
        const labelWidth = Math.max(54, metrics.width + 16);
        const labelY = Math.max(0, y - labelHeight);
        ctx.fillRect(x, labelY, labelWidth, labelHeight);
        ctx.fillStyle = "#f8fafc";
        ctx.fillText(label, x + 8, labelY + 15);
        ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      });

      return canvas.toDataURL("image/jpeg", 0.92);
    },
    [],
  );

  const stopActiveStream = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }
    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((track) => track.stop());
      activeStreamRef.current = null;
    }
  }, []);

  const startCamera = useCallback(async (): Promise<MediaStream | null> => {
    if (phaseMode === 0) {
      stopActiveStream();
      setIsCameraReady(false);
      return null;
    }

    try {
      setError(null);
      stopActiveStream();

      const attempts: MediaStreamConstraints[] = [
        { video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
        { video: { facingMode: "environment" }, audio: false },
        { video: true, audio: false },
      ];

      let stream: MediaStream | null = null;
      for (const constraints of attempts) {
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          break;
        } catch {
          // Continue through fallback constraints.
        }
      }

      if (!stream) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const firstVideo = devices.find((device) => device.kind === "videoinput");
        if (firstVideo?.deviceId) {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: firstVideo.deviceId } },
            audio: false,
          });
        }
      }
      if (!stream) {
        throw new Error("No camera stream available.");
      }

      if (videoRef.current) {
        videoRef.current.setAttribute("playsinline", "true");
        videoRef.current.setAttribute("muted", "true");
        videoRef.current.srcObject = stream;
        await new Promise<void>((resolve) => {
          if (!videoRef.current) {
            resolve();
            return;
          }
          videoRef.current.onloadedmetadata = () => resolve();
          // Some mobile browsers don't fire metadata promptly.
          window.setTimeout(() => resolve(), 500);
        });
        await videoRef.current.play();
      }
      activeStreamRef.current = stream;
      setIsCameraReady(true);
      return stream;
    } catch (cameraError) {
      const err = cameraError as Error & { name?: string };
      if (err.name === "NotAllowedError") {
        setError("Camera permission blocked. Allow camera access for this app and retry.");
      } else if (err.name === "NotReadableError") {
        setError("Camera is busy in another app/tab. Close other camera apps and retry.");
      } else {
        setError(`Camera unavailable: ${err.message}`);
      }
      setIsCameraReady(false);
      stopActiveStream();
      return null;
    }
  }, [phaseMode, stopActiveStream]);

  useEffect(() => {
    void startCamera();

    return () => {
      stopActiveStream();
    };
  }, [startCamera, stopActiveStream]);

  useEffect(() => {
    if (phaseMode === 0) {
      return;
    }
    const handleResume = () => {
      if (document.visibilityState === "visible") {
        void startCamera();
      }
    };
    document.addEventListener("visibilitychange", handleResume);
    window.addEventListener("focus", handleResume);
    window.addEventListener("pageshow", handleResume);
    return () => {
      document.removeEventListener("visibilitychange", handleResume);
      window.removeEventListener("focus", handleResume);
      window.removeEventListener("pageshow", handleResume);
    };
  }, [phaseMode, startCamera]);

  useEffect(() => {
    const previousHtmlOverscroll = document.documentElement.style.overscrollBehaviorY;
    const previousBodyOverscroll = document.body.style.overscrollBehaviorY;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlHeight = document.documentElement.style.height;
    const previousBodyHeight = document.body.style.height;
    const previousBodyMargin = document.body.style.margin;
    document.documentElement.style.overscrollBehaviorY = "none";
    document.body.style.overscrollBehaviorY = "none";
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    document.documentElement.style.height = "100%";
    document.body.style.height = "100%";
    document.body.style.margin = "0";

    return () => {
      document.documentElement.style.overscrollBehaviorY = previousHtmlOverscroll;
      document.body.style.overscrollBehaviorY = previousBodyOverscroll;
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.height = previousHtmlHeight;
      document.body.style.height = previousBodyHeight;
      document.body.style.margin = previousBodyMargin;
    };
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const installEvent = event as BeforeInstallPromptEvent;
      installEvent.preventDefault();
      setInstallPromptEvent(installEvent);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const triggerInstall = async () => {
    if (!installPromptEvent) {
      return;
    }
    await installPromptEvent.prompt();
    await installPromptEvent.userChoice;
    setInstallPromptEvent(null);
  };

  useEffect(() => {
    pushLog(`Backend mode selected: real (${processingModel})`);
  }, [processingModel, pushLog]);

  useEffect(() => {
    const runHealthCheck = async () => {
      try {
        const health = await getHealth();
        const pretty = JSON.stringify(health, null, 2);
        setBackendHealthJson(pretty);
        pushLog(`Health real (${processingModel}): ${health.status}`);
      } catch (healthError) {
        const msg = healthError instanceof Error ? healthError.message : "unknown health error";
        setBackendHealthJson(JSON.stringify({ error: msg }, null, 2));
        pushLog(`Health failed real (${processingModel}): ${msg}`);
      }
    };
    void runHealthCheck();
  }, [processingModel, pushLog]);

  const previousPhaseRef = useRef<number>(phaseMode);
  useEffect(() => {
    const previous = previousPhaseRef.current;
    previousPhaseRef.current = phaseMode;
    if (phaseMode === 0) {
      clearFallback();
      replaceOverlays([phase0DemoOverlay]);
      return;
    }
    // Only clear demo overlay when leaving phase 0, not on every non-zero phase change.
    if (previous === 0) {
      clearOverlays();
    }
  }, [phaseMode, clearFallback, clearOverlays, replaceOverlays]);

  useEffect(() => {
    if (!isFallbackActive || !fallbackData) {
      return;
    }
    const mapped = fallbackData.overlays.map((o, i) => ({
      id: `fallback-${i}`,
      bbox: { x: o.bbox[0], y: o.bbox[1], width: o.bbox[2], height: o.bbox[3] },
      label: o.label,
      confidence: o.confidence,
      ui_layer: LAYER_BY_INDEX[o.ui_layer] ?? "midground",
      overlay_type: TYPE_BY_NAME[o.overlay_type] ?? "info",
      action_required: o.action_required,
    }));
    replaceOverlays(mapped);
  }, [isFallbackActive, fallbackData, replaceOverlays]);

  useEffect(() => {
    setShowAgentToast(overlays.some((item) => item.action_required));
  }, [overlays]);

  const runAnalyze = async () => {
    if (phaseMode === 0) {
      return;
    }
    setError(null);
    try {
      pushLog(`Analyze start (real/${processingModel})`);
      const w = videoRef.current?.videoWidth ?? 0;
      const h = videoRef.current?.videoHeight ?? 0;
      const burst = await captureBurst(videoRef.current, multiPhotoCount, 85);
      const sortedBurst = [...burst].sort((a, b) => b.sharpnessScore - a.sharpnessScore);
      burstQueueRef.current = sortedBurst.map((shot) =>
        shot.dataUrl.includes(",") ? (shot.dataUrl.split(",")[1] ?? shot.dataUrl) : shot.dataUrl,
      );
      if (sortedBurst.length > 0) {
        setLastCaptureDataUrl(sortedBurst[0].dataUrl);
        lastCaptureDataUrlRef.current = sortedBurst[0].dataUrl;
      }

      let bestResponse: Awaited<ReturnType<typeof snapshot.runAnalysis>> | null = null;
      let bestConfidence = -1;
      const attempts = Math.max(1, Math.min(multiPhotoCount, sortedBurst.length || multiPhotoCount));
      for (let i = 0; i < attempts; i += 1) {
        const response = await snapshot.runAnalysis({
          query: "Scan this camera frame carefully and return one tight, accurate bounding box around the main subject.",
          sessionId: "aura-app-shell",
          captureTsMs: Date.now(),
          frameSize: w > 0 && h > 0 ? { width: w, height: h } : undefined,
          client: { platform: "web" },
        });
        const topConfidence = response.overlays[0]?.confidence ?? 0;
        if (topConfidence > bestConfidence) {
          bestConfidence = topConfidence;
          bestResponse = response;
        }
        if (response.overlays.length > 0 && topConfidence >= 0.8) {
          break;
        }
      }
      const response = bestResponse;
      if (!response) {
        throw new ApiClientError("No valid analysis response from captured photos.", "INVALID_RESPONSE");
      }
      hydrateFromResponse(response);
      setLastResponseJson(JSON.stringify(response, null, 2));
      const captureForPreview = lastCaptureDataUrlRef.current;
      if (captureForPreview) {
        try {
          const overlayPreview = await buildOverlayPreview(captureForPreview, response.overlays);
          setLastOverlayPreviewDataUrl(overlayPreview);
        } catch {
          setLastOverlayPreviewDataUrl(null);
        }
      }
      const firstLabel = response.overlays[0]?.label ?? "none";
      pushLog(`Analyze success (real/${processingModel}) overlays=${response.overlays.length} first=${firstLabel}`);
      burstQueueRef.current = [];
    } catch (analyzeError) {
      burstQueueRef.current = [];
      setLastOverlayPreviewDataUrl(null);
      setError(
        analyzeError instanceof ApiClientError
          ? analyzeError.message
          : (analyzeError as Error).message,
      );
      pushLog(
        `Analyze failed (real/${processingModel}): ${
          analyzeError instanceof Error ? analyzeError.message : "unknown error"
        }`,
      );
    }
  };

  const onProcessingModelChange = async (nextModel: ProcessingModel) => {
    if (nextModel === processingModel) {
      return;
    }
    try {
      const health = await getHealthForModel(nextModel);
      const models = (health as unknown as { models?: Record<string, string> }).models;
      const vlmStatus = models?.vlm ?? "unknown";
      const allowWarmingMoondream = nextModel === "moondream2" && vlmStatus === "loading";
      if (!models || (vlmStatus !== "ready" && !allowWarmingMoondream)) {
        const actual = models?.vlm ?? "unknown";
        throw new Error(`VLM is not ready (status=${actual})`);
      }
      setProcessingModel(nextModel);
      setProcessingModelState(nextModel);
      setError(null);
      if (allowWarmingMoondream) {
        setError("Moondream is warming up. First scan may take longer.");
      }
      pushLog(`Model switched to ${nextModel} (health=${health.status}, vlm=${vlmStatus})`);
    } catch (modelError) {
      const message =
        modelError instanceof Error
          ? modelError.message
          : `Model endpoint ${nextModel} is unavailable.`;
      setError(`Model "${nextModel}" unavailable: ${message}`);
      pushLog(`Model switch blocked for ${nextModel}: ${message}`);
    }
  };

  return (
    <main style={styles.app}>
      <section style={styles.stage}>
        <div style={styles.controlsTopLeft}>
          <span style={styles.backendBadge}>Backend: real / {processingModel}</span>
          {!isCameraReady && phaseMode > 0 ? (
            <button
              aria-label="Retry camera"
              onClick={() => {
                void startCamera();
              }}
              style={styles.utilityButton}
              type="button"
            >
              Retry Camera
            </button>
          ) : null}
          {installPromptEvent ? (
            <button
              aria-label="Install app"
              onClick={() => {
                void triggerInstall();
              }}
              style={styles.utilityButton}
              type="button"
            >
              Install App
            </button>
          ) : null}
          <button
            aria-label="Toggle logs view"
            onClick={() => setShowLogsView((value) => !value)}
            style={styles.utilityButton}
            type="button"
          >
            {showLogsView ? "Hide Logs" : "Show Logs"}
          </button>
        </div>
        <div style={styles.controlsTopRight}>
          <select
            aria-label="Multi photo count"
            id="multi-photo-count"
            value={multiPhotoCount}
            onChange={(event) => setMultiPhotoCount(Number(event.target.value))}
            style={styles.select}
          >
            <option value={1}>1 photo</option>
            <option value={3}>3 photos</option>
            <option value={5}>5 photos</option>
          </select>
          <select
            aria-label="Processing model"
            id="model-select"
            value={processingModel}
            onChange={(event) => {
              void onProcessingModelChange(event.target.value as ProcessingModel);
            }}
            style={styles.select}
          >
            {PROCESSING_MODEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            aria-label="Phase"
            id="phase-select"
            value={phaseMode}
            onChange={(event) => setPhaseMode(Number(event.target.value))}
            style={styles.select}
          >
            {PHASES.map((phase) => (
              <option key={phase} value={phase}>
                {phase} — {phaseLabels[phase]}
              </option>
            ))}
          </select>
        </div>
        {phaseMode === 0 ? (
          <FallbackVideo
            src="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
            isPlaying
            onTimeUpdate={() => undefined}
          />
        ) : (
          <video ref={videoRef} autoPlay style={styles.video} muted playsInline />
        )}
        <ScanReticle visible={phaseMode > 0} />
        <ScanAnimation isScanning={snapshot.isLoading} />
        <DepthHeatmap depthMap={phaseMode >= 5 ? new Float32Array([0.1, 0.2, 0.4, 0.8]) : null} width={2} height={2} />
        <OverlayCanvas overlays={overlays} />
        <button
          aria-label="Capture and analyze"
          disabled={phaseMode === 0}
          onClick={() => void runAnalyze()}
          style={styles.captureButton}
          type="button"
        >
          <span style={styles.captureButtonInner} />
        </button>
      </section>

      <footer style={styles.statusBar}>
        <span>Mode: {modeName}</span>
        <span>Backend: {backendTarget.mode}/{backendTarget.model}</span>
        <span>Camera: {isCameraReady || phaseMode === 0 ? "ready" : "not ready"}</span>
        <span>Overlay count: {overlays.length}</span>
        {overlays[0] ? <ConfidenceIndicator confidence={overlays[0].confidence} /> : null}
        {error ? <span style={styles.error}>Error: {error}</span> : <span>Connection: ready</span>}
        {snapshot.error ? <span style={styles.error}>API: {snapshot.error}</span> : null}
      </footer>
      <AgentActionToast
        message="Agent requested follow-up action"
        type={showAgentToast ? "triggered" : "resolved"}
        visible={showAgentToast}
        onDismiss={() => setShowAgentToast(false)}
      />
      {showLogsView ? (
        <aside style={styles.logsView}>
          <div style={styles.logsHeader}>
            <strong>Runtime Logs</strong>
            <button
              aria-label="Close logs view"
              onClick={() => setShowLogsView(false)}
              style={styles.utilityButton}
              type="button"
            >
              Close
            </button>
          </div>
          <div style={styles.logsGrid}>
            <section style={styles.logsSection}>
              <h3 style={styles.logsTitle}>Frontend Events</h3>
              <pre style={styles.preBlock}>{frontendLogs.join("\n") || "No events yet."}</pre>
            </section>
            <section style={styles.logsSection}>
              <h3 style={styles.logsTitle}>Backend Health</h3>
              <pre style={styles.preBlock}>{backendHealthJson || "No health check yet."}</pre>
            </section>
            <section style={styles.logsSection}>
              <h3 style={styles.logsTitle}>Last Capture</h3>
              {lastCaptureDataUrl ? (
                <img alt="Last captured frame" src={lastCaptureDataUrl} style={styles.capturePreview} />
              ) : (
                <pre style={styles.preBlock}>No capture yet.</pre>
              )}
            </section>
            <section style={styles.logsSection}>
              <h3 style={styles.logsTitle}>Last Analyze Response</h3>
              <pre style={styles.preBlock}>{lastResponseJson || "No analyze response yet."}</pre>
            </section>
            <section style={styles.logsSection}>
              <h3 style={styles.logsTitle}>Capture + Overlays</h3>
              {lastOverlayPreviewDataUrl ? (
                <img alt="Captured frame with overlays" src={lastOverlayPreviewDataUrl} style={styles.capturePreview} />
              ) : (
                <pre style={styles.preBlock}>No overlay preview yet.</pre>
              )}
            </section>
          </div>
        </aside>
      ) : null}
    </main>
  );
}

export default function App() {
  if (typeof window !== "undefined" && window.location.pathname === "/phone-capture") {
    return <PhoneCaptureApp />;
  }
  return <MainAuraApp />;
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    height: "100vh",
    display: "grid",
    gridTemplateRows: "1fr auto",
    background: "#030712",
    color: "#f9fafb",
    fontFamily: "Inter, system-ui, sans-serif",
    overscrollBehaviorY: "none",
    overflow: "hidden",
  },
  select: {
    padding: "0.45rem 0.7rem",
    borderRadius: "0.45rem",
    border: "1px solid #374151",
    background: "#111827",
    color: "#f9fafb",
    backdropFilter: "blur(6px)",
  },
  stage: {
    position: "relative",
    width: "100%",
    height: "100%",
    overflow: "hidden",
    background: "#000",
  },
  controlsTopLeft: {
    position: "absolute",
    top: "0.85rem",
    left: "0.85rem",
    zIndex: 1200,
    display: "flex",
    gap: "0.45rem",
    flexWrap: "wrap",
  },
  controlsTopRight: {
    position: "absolute",
    top: "0.85rem",
    right: "0.85rem",
    zIndex: 1200,
  },
  utilityButton: {
    padding: "0.42rem 0.62rem",
    borderRadius: "0.55rem",
    border: "1px solid #374151",
    background: "rgba(17,24,39,0.84)",
    color: "#f9fafb",
    fontSize: "0.8rem",
    cursor: "pointer",
    backdropFilter: "blur(6px)",
  },
  backendBadge: {
    display: "flex",
    alignItems: "center",
    padding: "0.42rem 0.62rem",
    borderRadius: "0.55rem",
    border: "1px solid #374151",
    background: "rgba(17,24,39,0.84)",
    color: "#f9fafb",
    fontSize: "0.8rem",
    backdropFilter: "blur(6px)",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  captureButton: {
    position: "absolute",
    left: "50%",
    bottom: "calc(5.75rem + env(safe-area-inset-bottom, 0px))",
    transform: "translateX(-50%)",
    width: "74px",
    height: "74px",
    borderRadius: "50%",
    border: "3px solid rgba(255,255,255,0.9)",
    background: "rgba(255,255,255,0.18)",
    display: "grid",
    placeItems: "center",
    cursor: "pointer",
    zIndex: 1200,
    padding: 0,
  },
  captureButtonInner: {
    width: "58px",
    height: "58px",
    borderRadius: "50%",
    background: "#ffffff",
    boxShadow: "0 0 0 2px rgba(255,255,255,0.6) inset",
  },
  statusBar: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    alignItems: "center",
    fontSize: "0.875rem",
    borderTop: "1px solid #1f2937",
    padding: "0.75rem 1rem",
    background: "rgba(3, 7, 18, 0.96)",
    zIndex: 1300,
  },
  error: {
    color: "#fca5a5",
  },
  logsView: {
    position: "fixed",
    inset: 0,
    background: "rgba(2, 6, 23, 0.96)",
    zIndex: 3000,
    padding: "0.9rem",
    display: "grid",
    gridTemplateRows: "auto 1fr",
    gap: "0.8rem",
    overflow: "auto",
  },
  logsHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  logsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.8rem",
  },
  logsSection: {
    background: "#0f172a",
    border: "1px solid #334155",
    borderRadius: "0.6rem",
    padding: "0.75rem",
    minHeight: "220px",
  },
  logsTitle: {
    margin: "0 0 0.5rem 0",
    fontSize: "0.92rem",
    color: "#e5e7eb",
  },
  preBlock: {
    margin: 0,
    fontSize: "0.75rem",
    color: "#cbd5e1",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: "300px",
    overflow: "auto",
  },
  capturePreview: {
    width: "100%",
    maxHeight: "300px",
    objectFit: "contain",
    borderRadius: "0.4rem",
    border: "1px solid #334155",
  },
};

const phoneStyles: Record<string, React.CSSProperties> = {
  arApp: {
    position: "relative",
    minHeight: "100vh",
    width: "100vw",
    overflow: "hidden",
    background: "#020617",
    color: "#e2e8f0",
    fontFamily: "Inter, system-ui, sans-serif",
  },
  backgroundCamera: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    objectFit: "cover",
    background: "black",
  },
  topHud: {
    position: "absolute",
    top: "env(safe-area-inset-top, 0px)",
    left: 0,
    right: 0,
    zIndex: 20,
    padding: "1rem 1rem 0.25rem",
    display: "flex",
    justifyContent: "center",
  },
  titleWrap: {
    width: "100%",
    maxWidth: "760px",
    borderRadius: "14px",
    border: "1px solid rgba(94, 125, 186, 0.45)",
    background: "rgba(3, 14, 36, 0.56)",
    backdropFilter: "blur(7px)",
    padding: "0.75rem 0.9rem",
  },
  arTitle: {
    margin: 0,
    fontSize: "1rem",
    fontWeight: 700,
    color: "#deebff",
    letterSpacing: "0.01em",
  },
  arSubtitle: {
    margin: "0.35rem 0 0",
    fontSize: "0.86rem",
    color: "#bed2ff",
  },
  stageRow: {
    marginTop: "0.45rem",
    display: "flex",
    flexWrap: "wrap",
    gap: "0.28rem",
  },
  stagePill: {
    fontSize: "0.62rem",
    lineHeight: 1,
    textTransform: "uppercase",
    letterSpacing: "0.03em",
    border: "1px solid rgba(104, 126, 165, 0.45)",
    background: "rgba(8, 21, 52, 0.62)",
    color: "#96aed8",
    borderRadius: "999px",
    padding: "0.24rem 0.4rem",
  },
  stagePillDone: {
    border: "1px solid rgba(88, 171, 132, 0.55)",
    background: "rgba(11, 51, 35, 0.55)",
    color: "#9fe5c1",
  },
  stagePillActive: {
    border: "1px solid rgba(115, 175, 255, 0.66)",
    background: "rgba(12, 44, 90, 0.68)",
    color: "#cde4ff",
    boxShadow: "0 0 0 1px rgba(113,170,255,0.16)",
  },
  overlayCard: {
    position: "absolute",
    left: "50%",
    top: "52%",
    transform: "translate(-50%, -50%)",
    width: "min(92vw, 760px)",
    borderRadius: "18px",
    border: "1px solid rgba(118, 170, 255, 0.52)",
    boxShadow: "0 0 0 1px rgba(110, 161, 255, 0.12), 0 18px 45px rgba(1, 8, 24, 0.56), 0 0 34px rgba(60, 141, 255, 0.25)",
    background: "rgba(5, 16, 40, 0.56)",
    backdropFilter: "blur(8px)",
    padding: "0.7rem",
    zIndex: 30,
    transition: "left 180ms ease, top 180ms ease, width 220ms ease, transform 220ms ease, opacity 220ms ease, box-shadow 260ms ease",
  },
  overlayVideo: {
    width: "100%",
    borderRadius: "12px",
    border: "1px solid rgba(149, 188, 255, 0.46)",
    background: "#030814",
    maxHeight: "58vh",
    objectFit: "contain",
  },
  resultControls: {
    display: "flex",
    justifyContent: "center",
    flexWrap: "wrap",
    gap: "0.55rem",
    marginTop: "0.55rem",
  },
  resultButton: {
    padding: "0.52rem 0.72rem",
    borderRadius: "999px",
    border: "1px solid rgba(124, 154, 213, 0.62)",
    background: "rgba(5, 17, 43, 0.74)",
    color: "#e1ecff",
    fontSize: "0.82rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  resultLink: {
    padding: "0.52rem 0.72rem",
    borderRadius: "999px",
    border: "1px solid rgba(124, 154, 213, 0.62)",
    background: "rgba(5, 17, 43, 0.74)",
    color: "#9ec4ff",
    fontSize: "0.82rem",
    fontWeight: 600,
    textDecoration: "none",
  },
  captureCta: {
    position: "absolute",
    left: "50%",
    bottom: "calc(env(safe-area-inset-bottom, 0px) + 1.5rem)",
    transform: "translateX(-50%)",
    zIndex: 40,
    borderRadius: "999px",
    border: "1px solid rgba(120, 170, 255, 0.65)",
    background: "linear-gradient(180deg, rgba(57,127,255,0.94), rgba(41,99,228,0.9))",
    color: "white",
    fontWeight: 700,
    fontSize: "0.95rem",
    letterSpacing: "0.01em",
    padding: "0.88rem 1.35rem",
    minWidth: "190px",
    cursor: "pointer",
    boxShadow: "0 12px 30px rgba(19, 84, 210, 0.5)",
  },
  fallbackRow: {
    position: "absolute",
    right: "0.7rem",
    bottom: "calc(env(safe-area-inset-bottom, 0px) + 0.65rem)",
    zIndex: 45,
    display: "grid",
    gap: "0.4rem",
  },
  fallbackToggle: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.45rem",
    padding: "0.42rem 0.58rem",
    borderRadius: "10px",
    border: "1px solid rgba(93, 126, 186, 0.42)",
    background: "rgba(4, 16, 42, 0.58)",
    fontSize: "0.72rem",
    color: "#bcd5ff",
    backdropFilter: "blur(6px)",
  },
  captureFlash: {
    position: "absolute",
    inset: 0,
    background: "rgba(255,255,255,0.2)",
    zIndex: 35,
    pointerEvents: "none",
  },
  cameraError: {
    position: "absolute",
    left: "50%",
    transform: "translateX(-50%)",
    bottom: "calc(env(safe-area-inset-bottom, 0px) + 5.1rem)",
    margin: 0,
    fontSize: "0.78rem",
    color: "#ffd0d8",
    background: "rgba(64, 18, 28, 0.78)",
    border: "1px solid rgba(251, 146, 170, 0.45)",
    borderRadius: "8px",
    padding: "0.38rem 0.52rem",
    zIndex: 45,
  },
  freezePreview: {
    position: "absolute",
    right: "0.7rem",
    top: "calc(env(safe-area-inset-top, 0px) + 5rem)",
    width: "92px",
    aspectRatio: "3 / 4",
    objectFit: "cover",
    borderRadius: "10px",
    border: "1px solid rgba(135, 167, 219, 0.66)",
    boxShadow: "0 10px 22px rgba(2, 8, 24, 0.5)",
    zIndex: 45,
  },
};
