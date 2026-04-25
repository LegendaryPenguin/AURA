from __future__ import annotations

import base64
import io
from typing import Tuple

from PIL import Image


def encode_base64(data: bytes) -> str:
    """Encode bytes into a UTF-8 base64 string."""
    return base64.b64encode(data).decode("utf-8")


def decode_base64(data_b64: str) -> bytes:
    """Decode a UTF-8 base64 string into bytes."""
    return base64.b64decode(data_b64.encode("utf-8"), validate=True)


def decode_jpeg(image_bytes: bytes) -> Image.Image:
    """Load JPEG bytes as a PIL image in RGB format."""
    with io.BytesIO(image_bytes) as buffer:
        image = Image.open(buffer)
        if image.format != "JPEG":
            raise ValueError("Expected JPEG image bytes")
        return image.convert("RGB")


def encode_jpeg(image: Image.Image, quality: int = 95) -> bytes:
    """Encode PIL image as JPEG bytes."""
    with io.BytesIO() as buffer:
        image.convert("RGB").save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def resize_with_aspect_ratio(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """
    Resize while preserving aspect ratio, padding with black bars as needed.

    The resulting image always has exact target dimensions.
    """
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target_width and target_height must be positive")

    src_width, src_height = image.size
    ratio = min(target_width / src_width, target_height / src_height)
    resized = image.resize((max(1, int(src_width * ratio)), max(1, int(src_height * ratio))), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (target_width, target_height), (0, 0, 0))
    paste_x = (target_width - resized.size[0]) // 2
    paste_y = (target_height - resized.size[1]) // 2
    canvas.paste(resized, (paste_x, paste_y))
    return canvas


def round_trip_jpeg(image_bytes: bytes, target_width: int, target_height: int) -> Tuple[bytes, Image.Image]:
    """
    Decode JPEG bytes, resize, and re-encode.

    Returns the re-encoded bytes plus the resized PIL image for callers that need
    dimensions/inspection without decoding twice.
    """
    image = decode_jpeg(image_bytes)
    resized = resize_with_aspect_ratio(image, target_width, target_height)
    return encode_jpeg(resized), resized
