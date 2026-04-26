import { useCallback, useRef, useState } from "react";
import type { SnapshotAudioPayload } from "../types/overlay";

export interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<SnapshotAudioPayload | undefined>;
  holdToRecord: () => Promise<() => Promise<SnapshotAudioPayload | undefined>>;
  error: string | null;
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.split(",")[1] ?? "";
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Failed to read audio blob"));
    reader.readAsDataURL(blob);
  });
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.start(100);
      setIsRecording(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Microphone unavailable";
      setError(msg);
    }
  }, []);

  const stopRecording = useCallback(async (): Promise<SnapshotAudioPayload | undefined> => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setIsRecording(false);
      return undefined;
    }

    return new Promise<SnapshotAudioPayload | undefined>((resolve) => {
      recorder.onstop = async () => {
        setIsRecording(false);
        recorder.stream.getTracks().forEach((t) => t.stop());
        mediaRecorderRef.current = null;

        if (chunksRef.current.length === 0) {
          resolve(undefined);
          return;
        }

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];

        try {
          const audioBase64 = await blobToBase64(blob);
          resolve({
            audioBase64,
            audioFormat: "webm",
          });
        } catch {
          resolve(undefined);
        }
      };

      recorder.stop();
    });
  }, []);

  const holdToRecord = useCallback(async () => {
    await startRecording();
    return stopRecording;
  }, [startRecording, stopRecording]);

  return { isRecording, startRecording, stopRecording, holdToRecord, error };
}
