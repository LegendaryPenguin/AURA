import { useCallback, useMemo, useRef, useState } from "react";

import type { SnapshotAudioPayload, SupportedAudioFormat } from "../types/overlay";

const MAX_RECORDING_MS = 3000;

const toBase64 = async (blob: Blob): Promise<string> => {
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

export interface UseAudioRecorderReturn {
  isRecording: boolean;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<SnapshotAudioPayload | undefined>;
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timeoutRef = useRef<number | null>(null);
  const resolveRef = useRef<((value: SnapshotAudioPayload | undefined) => void) | null>(null);

  const stopRecording = useCallback(async (): Promise<SnapshotAudioPayload | undefined> => {
    if (!recorderRef.current) {
      return undefined;
    }
    const recorder = recorderRef.current;
    return new Promise<SnapshotAudioPayload | undefined>((resolve) => {
      resolveRef.current = resolve;
      recorder.stop();
    });
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        recorderRef.current = null;
        setIsRecording(false);
        if (timeoutRef.current) {
          window.clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        if (blob.size === 0) {
          resolveRef.current?.(undefined);
          resolveRef.current = null;
          return;
        }
        const base64 = await toBase64(blob);
        const format: SupportedAudioFormat = "webm";
        resolveRef.current?.({ audioBase64: base64, audioFormat: format });
        resolveRef.current = null;
      };
      recorder.start();
      setError(null);
      setIsRecording(true);
      timeoutRef.current = window.setTimeout(() => {
        void stopRecording();
      }, MAX_RECORDING_MS);
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "Microphone access failed");
      setIsRecording(false);
    }
  }, [stopRecording]);

  return useMemo(
    () => ({ isRecording, error, startRecording, stopRecording }),
    [error, isRecording, startRecording, stopRecording],
  );
}
