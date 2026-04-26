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
  getBackendTarget,
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
  status_url: string;
  video_url: string;
}

interface VideoSimJobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  message?: string;
  error?: string | null;
  video_url?: string;
  elapsed_seconds?: number;
}

function resolveApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const target = getBackendTarget().baseUrl;
  const alreadyApiPrefixed = normalized.startsWith("/api/");
  if (!target) {
    return alreadyApiPrefixed ? normalized : `/api${normalized}`;
  }
  return `${target}${normalized}`;
}

function PhoneCaptureApp() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string>("");
  const [status, setStatus] = useState<VideoSimJobStatusResponse["status"] | "idle">("idle");
  const [statusMessage, setStatusMessage] = useState<string>("Point camera at your equation and tap capture.");
  const [videoUrl, setVideoUrl] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [cameraReady, setCameraReady] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string>("");
  const [captureFlash, setCaptureFlash] = useState<boolean>(false);
  const [showOverlayVideo, setShowOverlayVideo] = useState<boolean>(false);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const overlayVideoRef = useRef<HTMLVideoElement | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);

  const statusStory = useMemo(() => {
    if (status === "queued") return "Uploading captured frame...";
    if (status === "running") return "Composing AR tutorial...";
    if (status === "done") return "AR tutorial ready.";
    if (status === "error") return statusMessage || "Generation failed.";
    return statusMessage;
  }, [status, statusMessage]);

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
          const elapsed = typeof payload.elapsed_seconds === "number" ? ` (${payload.elapsed_seconds}s)` : "";
          setStatusMessage(`${payload.message || payload.status}${elapsed}`);
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
          setStatus("error");
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

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    setVideoUrl("");
    setJobId("");
    setStatus("idle");
    setStatusMessage(nextFile ? "Image selected." : "Ready to capture.");
    setShowOverlayVideo(false);
  };

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
    setStatusMessage("Captured. Starting generation...");
    setShowOverlayVideo(false);
    setCaptureFlash(true);
    window.setTimeout(() => setCaptureFlash(false), 180);
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
    setStatusMessage("Uploading captured frame...");
    setVideoUrl("");
    setShowOverlayVideo(false);
    try {
      const form = new FormData();
      form.append("image", sourceFile, sourceFile.name || "capture.jpg");
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
      setStatusMessage("Composing AR tutorial...");
    } catch (err) {
      setStatus("error");
      setStatusMessage(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const onPrimaryCapture = async () => {
    if (!cameraReady || isSubmitting) {
      return;
    }
    const file = await captureFromCamera();
    if (!file) {
      return;
    }
    await onGenerate(file);
  };

  const onRetake = async () => {
    setJobId("");
    setStatus("idle");
    setStatusMessage("Point camera at your equation and tap capture.");
    setShowOverlayVideo(false);
    setVideoUrl("");
    await startCamera();
  };

  return (
    <main style={phoneStyles.arApp}>
      <video autoPlay muted playsInline ref={cameraVideoRef} style={phoneStyles.backgroundCamera} />
      {captureFlash ? <div style={phoneStyles.captureFlash} /> : null}

      <div style={phoneStyles.topHud}>
        <div style={phoneStyles.titleWrap}>
          <h1 style={phoneStyles.arTitle}>AURA AR Tutor</h1>
          <p style={phoneStyles.arSubtitle}>{statusStory}</p>
        </div>
      </div>

      {showOverlayVideo && videoUrl ? (
        <section style={phoneStyles.overlayCard}>
          <video controls playsInline ref={overlayVideoRef} src={videoUrl} style={phoneStyles.overlayVideo} />
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
        <label style={phoneStyles.fallbackLabel}>
          <span>Fallback upload</span>
          <input accept="image/*" capture="environment" onChange={onFileChange} style={phoneStyles.fileInput} type="file" />
        </label>
      </div>
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

  const { captureFrame } = useFrameCapture();
  const {
    overlays,
    clearOverlays,
    hydrateFromResponse,
    replaceOverlays,
  } = useOverlay({ autoDismissMs: 60_000 });
  const { fallbackData, isFallbackActive, clearFallback } = useFallback();

  const captureForApi = useCallback(() => {
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
  const backendTarget = useMemo(() => getBackendTarget(), []);

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
    pushLog("Backend mode selected: real");
  }, [pushLog]);

  useEffect(() => {
    const runHealthCheck = async () => {
      try {
        const health = await getHealth();
        const pretty = JSON.stringify(health, null, 2);
        setBackendHealthJson(pretty);
        pushLog(`Health real: ${health.status}`);
      } catch (healthError) {
        const msg = healthError instanceof Error ? healthError.message : "unknown health error";
        setBackendHealthJson(JSON.stringify({ error: msg }, null, 2));
        pushLog(`Health failed real: ${msg}`);
      }
    };
    void runHealthCheck();
  }, [pushLog]);

  useEffect(() => {
    if (phaseMode === 0) {
      clearFallback();
      replaceOverlays([phase0DemoOverlay]);
    } else {
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
      pushLog("Analyze start (real)");
      const w = videoRef.current?.videoWidth ?? 0;
      const h = videoRef.current?.videoHeight ?? 0;
      const response = await snapshot.runAnalysis({
        query: "What am I looking at?",
        sessionId: "aura-app-shell",
        captureTsMs: Date.now(),
        frameSize: w > 0 && h > 0 ? { width: w, height: h } : undefined,
        client: { platform: "web" },
      });
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
      pushLog(`Analyze success (real) overlays=${response.overlays.length} first=${firstLabel}`);
    } catch (analyzeError) {
      clearOverlays();
      setLastOverlayPreviewDataUrl(null);
      setError(
        analyzeError instanceof ApiClientError
          ? analyzeError.message
          : (analyzeError as Error).message,
      );
      pushLog(
        `Analyze failed (real): ${
          analyzeError instanceof Error ? analyzeError.message : "unknown error"
        }`,
      );
    }
  };

  return (
    <main style={styles.app}>
      <section style={styles.stage}>
        <div style={styles.controlsTopLeft}>
          <span style={styles.backendBadge}>Backend: real</span>
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
          disabled={snapshot.isLoading || phaseMode === 0}
          onClick={() => void runAnalyze()}
          style={styles.captureButton}
          type="button"
        >
          <span style={styles.captureButtonInner} />
        </button>
      </section>

      <footer style={styles.statusBar}>
        <span>Mode: {modeName}</span>
        <span>Backend: {backendTarget.mode}</span>
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
  },
  fallbackLabel: {
    display: "grid",
    gap: "0.25rem",
    padding: "0.48rem 0.58rem",
    borderRadius: "10px",
    border: "1px solid rgba(93, 126, 186, 0.42)",
    background: "rgba(4, 16, 42, 0.58)",
    fontSize: "0.7rem",
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
  fileInput: {
    border: "1px solid #334155",
    borderRadius: "8px",
    background: "#0f172a",
    color: "#e2e8f0",
    padding: "0.3rem",
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
};
