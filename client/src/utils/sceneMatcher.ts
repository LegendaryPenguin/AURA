import type { DemoScenarioId } from "../data/demoScenarios";

type MatchableScenario = Exclude<DemoScenarioId, "free">;
type DetectableScenario = Extract<MatchableScenario, "care" | "sustainability" | "wayfinding">;

interface SceneReference {
  id: DetectableScenario;
  path: string;
}

const SCENE_REFERENCES: SceneReference[] = [
  { id: "care", path: "/demo-scenes/medical1.png" },
  { id: "sustainability", path: "/demo-scenes/sustainability2.png" },
  { id: "wayfinding", path: "/demo-scenes/wayfinding3.png" },
];

const HASH_SIZE = 16;
const MIN_CONFIDENCE = 0.72;

const hashCache = new Map<string, Promise<Uint8Array | null>>();

function hashFromImageSource(source: CanvasImageSource): Uint8Array {
  const canvas = document.createElement("canvas");
  canvas.width = HASH_SIZE;
  canvas.height = HASH_SIZE;
  const context = canvas.getContext("2d");
  if (!context) {
    return new Uint8Array(HASH_SIZE * HASH_SIZE);
  }
  context.drawImage(source, 0, 0, HASH_SIZE, HASH_SIZE);
  const imageData = context.getImageData(0, 0, HASH_SIZE, HASH_SIZE);
  const grays = new Uint8Array(HASH_SIZE * HASH_SIZE);
  let total = 0;
  for (let i = 0; i < grays.length; i += 1) {
    const r = imageData.data[i * 4];
    const g = imageData.data[i * 4 + 1];
    const b = imageData.data[i * 4 + 2];
    const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
    grays[i] = gray;
    total += gray;
  }
  const avg = total / grays.length;
  const bits = new Uint8Array(grays.length);
  for (let i = 0; i < grays.length; i += 1) {
    bits[i] = grays[i] >= avg ? 1 : 0;
  }
  return bits;
}

function hammingDistance(a: Uint8Array, b: Uint8Array): number {
  const length = Math.min(a.length, b.length);
  let diff = 0;
  for (let i = 0; i < length; i += 1) {
    if (a[i] !== b[i]) {
      diff += 1;
    }
  }
  return diff + Math.abs(a.length - b.length);
}

async function loadHashFromPath(path: string): Promise<Uint8Array | null> {
  const cached = hashCache.get(path);
  if (cached) {
    return cached;
  }
  const promise = new Promise<Uint8Array | null>((resolve) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(hashFromImageSource(image));
    image.onerror = () => resolve(null);
    image.src = path;
  });
  hashCache.set(path, promise);
  return promise;
}

export async function detectScenarioFromCapture(capturedDataUrl: string): Promise<DetectableScenario | null> {
  const captureImage = await new Promise<HTMLImageElement | null>((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = capturedDataUrl;
  });
  if (!captureImage) {
    return null;
  }
  const captureHash = hashFromImageSource(captureImage);

  let best: { id: DetectableScenario | null; confidence: number } = { id: null, confidence: 0 };
  for (const reference of SCENE_REFERENCES) {
    const referenceHash = await loadHashFromPath(reference.path);
    if (!referenceHash) {
      continue;
    }
    const distance = hammingDistance(captureHash, referenceHash);
    const confidence = 1 - distance / captureHash.length;
    if (confidence > best.confidence) {
      best = { id: reference.id, confidence };
    }
  }

  if (best.confidence < MIN_CONFIDENCE) {
    return null;
  }
  return best.id;
}
