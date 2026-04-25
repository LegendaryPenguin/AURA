from __future__ import annotations

import io

import pytest
from PIL import Image

from server.utils.image_utils import (
    decode_base64,
    decode_jpeg,
    encode_base64,
    encode_jpeg,
    resize_with_aspect_ratio,
    round_trip_jpeg,
)


def _make_jpeg_bytes(size: tuple[int, int] = (120, 80), color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    image = Image.new("RGB", size, color)
    return encode_jpeg(image)


def test_base64_round_trip_identity() -> None:
    payload = b"\x00aura\xffbinary"
    encoded = encode_base64(payload)
    decoded = decode_base64(encoded)
    assert decoded == payload


def test_decode_jpeg_rejects_non_jpeg_bytes() -> None:
    image = Image.new("RGB", (32, 32), (0, 255, 0))
    with io.BytesIO() as buffer:
        image.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

    with pytest.raises(ValueError, match="Expected JPEG image bytes"):
        decode_jpeg(png_bytes)


def test_resize_with_aspect_ratio_outputs_target_dimensions() -> None:
    source = Image.new("RGB", (200, 100), (20, 30, 40))
    resized = resize_with_aspect_ratio(source, target_width=300, target_height=300)

    assert resized.size == (300, 300)
    assert resized.getpixel((150, 150)) == (20, 30, 40)
    assert resized.getpixel((0, 0)) == (0, 0, 0)


def test_round_trip_jpeg_returns_valid_resized_jpeg() -> None:
    input_bytes = _make_jpeg_bytes(size=(180, 120), color=(3, 4, 5))
    output_bytes, resized_image = round_trip_jpeg(input_bytes, target_width=90, target_height=90)

    assert resized_image.size == (90, 90)

    decoded = decode_jpeg(output_bytes)
    assert decoded.size == (90, 90)
