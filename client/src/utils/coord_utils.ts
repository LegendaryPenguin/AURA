export interface NormalizedBbox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PixelRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface CoverCompensation {
  scale: number;
  croppedSourceWidth: number;
  croppedSourceHeight: number;
  sourceOffsetX: number;
  sourceOffsetY: number;
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

export function clampNormalizedBbox(bbox: NormalizedBbox): NormalizedBbox {
  const x1 = clamp(bbox.x);
  const y1 = clamp(bbox.y);
  const x2 = clamp(bbox.x + bbox.width);
  const y2 = clamp(bbox.y + bbox.height);

  return {
    x: x1,
    y: y1,
    width: Math.max(0, x2 - x1),
    height: Math.max(0, y2 - y1)
  };
}

export function normalizeRect(rect: PixelRect, frame: Size): NormalizedBbox {
  if (frame.width <= 0 || frame.height <= 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }

  return clampNormalizedBbox({
    x: rect.left / frame.width,
    y: rect.top / frame.height,
    width: rect.width / frame.width,
    height: rect.height / frame.height
  });
}

export function denormalizeRect(normalized: NormalizedBbox, frame: Size): PixelRect {
  const clamped = clampNormalizedBbox(normalized);

  return {
    left: clamped.x * frame.width,
    top: clamped.y * frame.height,
    width: clamped.width * frame.width,
    height: clamped.height * frame.height
  };
}

export function getContainFit(media: Size, container: Size): { scale: number; renderedWidth: number; renderedHeight: number; offsetX: number; offsetY: number } {
  if (media.width <= 0 || media.height <= 0 || container.width <= 0 || container.height <= 0) {
    return { scale: 1, renderedWidth: container.width, renderedHeight: container.height, offsetX: 0, offsetY: 0 };
  }

  const scale = Math.min(container.width / media.width, container.height / media.height);
  const renderedWidth = media.width * scale;
  const renderedHeight = media.height * scale;

  return {
    scale,
    renderedWidth,
    renderedHeight,
    offsetX: (container.width - renderedWidth) / 2,
    offsetY: (container.height - renderedHeight) / 2
  };
}

export function getCoverCompensation(media: Size, container: Size): CoverCompensation {
  if (media.width <= 0 || media.height <= 0 || container.width <= 0 || container.height <= 0) {
    return {
      scale: 1,
      croppedSourceWidth: media.width,
      croppedSourceHeight: media.height,
      sourceOffsetX: 0,
      sourceOffsetY: 0
    };
  }

  const scale = Math.max(container.width / media.width, container.height / media.height);
  const sourceVisibleWidth = container.width / scale;
  const sourceVisibleHeight = container.height / scale;

  return {
    scale,
    croppedSourceWidth: sourceVisibleWidth,
    croppedSourceHeight: sourceVisibleHeight,
    sourceOffsetX: (media.width - sourceVisibleWidth) / 2,
    sourceOffsetY: (media.height - sourceVisibleHeight) / 2
  };
}

export function mapNormalizedToCoverSpace(normalized: NormalizedBbox, media: Size, container: Size): NormalizedBbox {
  const clamped = clampNormalizedBbox(normalized);
  const crop = getCoverCompensation(media, container);

  if (media.width <= 0 || media.height <= 0 || crop.croppedSourceWidth <= 0 || crop.croppedSourceHeight <= 0) {
    return clamped;
  }

  const sourceLeft = clamped.x * media.width;
  const sourceTop = clamped.y * media.height;
  const sourceWidth = clamped.width * media.width;
  const sourceHeight = clamped.height * media.height;

  const mappedLeft = ((sourceLeft - crop.sourceOffsetX) / crop.croppedSourceWidth);
  const mappedTop = ((sourceTop - crop.sourceOffsetY) / crop.croppedSourceHeight);
  const mappedWidth = sourceWidth / crop.croppedSourceWidth;
  const mappedHeight = sourceHeight / crop.croppedSourceHeight;

  return clampNormalizedBbox({
    x: mappedLeft,
    y: mappedTop,
    width: mappedWidth,
    height: mappedHeight
  });
}
