import {
  type NormalizedBbox,
  type PixelRect,
  type Size,
  denormalizeRect,
  mapNormalizedToCoverSpace
} from "../utils/coord_utils";

export interface OverlayMapperInput {
  normalized: NormalizedBbox;
  videoElement: HTMLVideoElement;
  sourceSize?: Size;
}

export interface OverlayMapper {
  toPixelRect: (input: OverlayMapperInput) => PixelRect;
}

function getVideoSourceSize(videoElement: HTMLVideoElement, sourceSize?: Size): Size {
  if (sourceSize && sourceSize.width > 0 && sourceSize.height > 0) {
    return sourceSize;
  }

  return {
    width: videoElement.videoWidth || videoElement.clientWidth || 0,
    height: videoElement.videoHeight || videoElement.clientHeight || 0
  };
}

function toContainerSize(videoElement: HTMLVideoElement): Size {
  const bounds = videoElement.getBoundingClientRect();

  return {
    width: bounds.width,
    height: bounds.height
  };
}

export function mapNormalizedOverlayToPixels(input: OverlayMapperInput): PixelRect {
  const { normalized, videoElement, sourceSize } = input;
  const bounds = videoElement.getBoundingClientRect();
  const containerSize = toContainerSize(videoElement);
  const mediaSize = getVideoSourceSize(videoElement, sourceSize);

  const normalizedWithinCover = mapNormalizedToCoverSpace(normalized, mediaSize, containerSize);
  const localRect = denormalizeRect(normalizedWithinCover, containerSize);

  return {
    left: bounds.left + localRect.left,
    top: bounds.top + localRect.top,
    width: localRect.width,
    height: localRect.height
  };
}

export function createOverlayMapper(): OverlayMapper {
  return {
    toPixelRect: mapNormalizedOverlayToPixels
  };
}
