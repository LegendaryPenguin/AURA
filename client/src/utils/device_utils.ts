export interface DeviceCapabilities {
  supportsMediaDevices: boolean;
  supportsAudioRecording: boolean;
  orientation: "portrait" | "landscape";
  viewport: { width: number; height: number };
}

export const getOrientation = (): "portrait" | "landscape" =>
  window.innerHeight >= window.innerWidth ? "portrait" : "landscape";

export const getViewport = (): { width: number; height: number } => ({
  width: window.innerWidth,
  height: window.innerHeight,
});

export const getDeviceCapabilities = (): DeviceCapabilities => ({
  supportsMediaDevices: Boolean(navigator.mediaDevices?.getUserMedia),
  supportsAudioRecording: typeof MediaRecorder !== "undefined",
  orientation: getOrientation(),
  viewport: getViewport(),
});
