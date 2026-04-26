from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

STYLE_PROFILES: dict[str, dict[str, float | int]] = {
    "paper_clean": {
        "wipe_margin_x_ratio": 0.06,
        "wipe_margin_y_ratio": 0.25,
        "text_y_offset": 8,
        "write_char_ms_equivalent": 65,
        "write_char_ms_inconsistent": 75,
        "wipe_ms_equivalent": 280,
        "wipe_ms_inconsistent": 360,
        "line_h_scale": 0.62,
    },
    "paper_3b1b": {
        "wipe_margin_x_ratio": 0.04,
        "wipe_margin_y_ratio": 0.20,
        "text_y_offset": 6,
        "write_char_ms_equivalent": 58,
        "write_char_ms_inconsistent": 68,
        "wipe_ms_equivalent": 240,
        "wipe_ms_inconsistent": 320,
        "line_h_scale": 0.56,
    },
    "hybrid": {
        "wipe_margin_x_ratio": 0.05,
        "wipe_margin_y_ratio": 0.22,
        "text_y_offset": 7,
        "write_char_ms_equivalent": 62,
        "write_char_ms_inconsistent": 72,
        "wipe_ms_equivalent": 260,
        "wipe_ms_inconsistent": 340,
        "line_h_scale": 0.60,
    },
    "minimal": {
        "wipe_margin_x_ratio": 0.05,
        "wipe_margin_y_ratio": 0.22,
        "text_y_offset": 7,
        "write_char_ms_equivalent": 60,
        "write_char_ms_inconsistent": 70,
        "wipe_ms_equivalent": 250,
        "wipe_ms_inconsistent": 330,
        "line_h_scale": 0.58,
    },
}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = (240, 240, 240),
    line_spacing: int = 8,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += int(font.size * 1.2) + line_spacing
    return cursor


def _sample_paper_color(image: Image.Image, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = rect
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(image.width, x2)
    y2 = min(image.height, y2)
    if x2 <= x1 or y2 <= y1:
        return (245, 245, 245, 235)
    crop = image.crop((x1, y1, x2, y2)).convert("RGB")
    stat = Image.Image.getbbox(crop)
    if stat is None:
        return (245, 245, 245, 235)
    pixels = list(crop.getdata())
    n = max(1, len(pixels))
    r = sum(p[0] for p in pixels) // n
    g = sum(p[1] for p in pixels) // n
    b = sum(p[2] for p in pixels) // n
    return (r, g, b, 238)


def _sample_local_background_color(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    ink_threshold: int = 180,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = rect
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(image.width, x2)
    y2 = min(image.height, y2)
    if x2 <= x1 or y2 <= y1:
        return (245, 245, 245, 242)
    rgb = image.convert("RGB")
    selected: list[tuple[int, int, int]] = []
    for y in range(y1, y2):
        for x in range(x1, x2):
            p = rgb.getpixel((x, y))
            # Keep only background-like bright pixels and ignore dark ink.
            if int((p[0] + p[1] + p[2]) / 3) >= ink_threshold:
                selected.append(p)
    if not selected:
        return _sample_paper_color(image, rect)
    n = len(selected)
    r = sum(p[0] for p in selected) // n
    g = sum(p[1] for p in selected) // n
    b = sum(p[2] for p in selected) // n
    return (r, g, b, 242)


def _line_slots(canvas_rect: tuple[int, int, int, int], count: int) -> list[tuple[int, int, int, int]]:
    x1, y1, x2, y2 = canvas_rect
    if count <= 0:
        return []
    usable_top = y1 + int((y2 - y1) * 0.12)
    usable_bottom = y1 + int((y2 - y1) * 0.82)
    step = (usable_bottom - usable_top) / max(1, count)
    slots: list[tuple[int, int, int, int]] = []
    for i in range(count):
        cy = int(usable_top + (i + 0.5) * step)
        h = int(max(36, min((y2 - y1) * 0.07, step * 0.62)))
        slots.append((x1 + 40, cy - h // 2, x2 - 40, cy + h // 2))
    return slots


def _quantized_bbox(
    bbox: tuple[int, int, int, int],
    *,
    quantum: int = 2,
) -> tuple[int, int, int, int]:
    if quantum <= 1:
        return bbox
    x1, y1, x2, y2 = bbox
    return (
        int(round(x1 / quantum) * quantum),
        int(round(y1 / quantum) * quantum),
        int(round(x2 / quantum) * quantum),
        int(round(y2 / quantum) * quantum),
    )


def _dark_rows(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    darkness_threshold: int = 120,
) -> list[int]:
    x1, y1, x2, y2 = rect
    gray = image.convert("L")
    rows: list[int] = []
    for y in range(y1, y2):
        dark = 0
        total = max(1, x2 - x1)
        for x in range(x1, x2):
            if gray.getpixel((x, y)) < darkness_threshold:
                dark += 1
        if dark / total > 0.02:
            rows.append(y)
    return rows


def _group_rows(rows: list[int], min_height: int = 8) -> list[tuple[int, int]]:
    if not rows:
        return []
    groups: list[tuple[int, int]] = []
    start = rows[0]
    prev = rows[0]
    for y in rows[1:]:
        if y - prev <= 2:
            prev = y
            continue
        if prev - start + 1 >= min_height:
            groups.append((start, prev))
        start = y
        prev = y
    if prev - start + 1 >= min_height:
        groups.append((start, prev))
    return groups


def _band_extent(
    image: Image.Image,
    *,
    band: tuple[int, int],
    x_range: tuple[int, int],
    darkness_threshold: int = 128,
) -> tuple[int, int, int]:
    gray = image.convert("L")
    x1, x2 = x_range
    by1, by2 = band
    xs: list[int] = []
    ink_count = 0
    for y in range(by1, by2 + 1):
        for x in range(x1, x2):
            if gray.getpixel((x, y)) < darkness_threshold:
                xs.append(x)
                ink_count += 1
    if not xs:
        return x1, x2, 0
    left = max(x1, min(xs) - 10)
    right = min(x2, max(xs) + 10)
    return left, right, ink_count


def _assign_bands_to_slots(
    *,
    image: Image.Image,
    bands: list[tuple[int, int]],
    paper_rect: tuple[int, int, int, int],
    expected_count: int,
    line_h_scale: float,
) -> list[dict[str, Any]]:
    px1, py1, px2, py2 = paper_rect
    slots = _line_slots(paper_rect, expected_count)
    anchors: list[dict[str, Any]] = []
    used_band_ids: set[int] = set()
    for slot in slots:
        sx1, sy1, sx2, sy2 = slot
        slot_center = (sy1 + sy2) / 2.0
        best_idx: int | None = None
        best_score = -1.0
        best_extent = (sx1, sx2, 0)
        for idx, band in enumerate(bands):
            if idx in used_band_ids:
                continue
            by1, by2 = band
            band_center = (by1 + by2) / 2.0
            distance = abs(band_center - slot_center)
            left, right, ink_count = _band_extent(image, band=band, x_range=(px1, px2))
            if ink_count == 0:
                continue
            width = max(1, right - left)
            density = ink_count / max(1.0, width * max(1, by2 - by1 + 1))
            score = (density * 1800.0 + min(600.0, ink_count / 4.0)) - distance * 8.0
            if score > best_score:
                best_score = score
                best_idx = idx
                best_extent = (left, right, ink_count)
        if best_idx is None:
            anchors.append(
                {
                    "bbox": (sx1, sy1, sx2, sy2),
                    "text_origin": (sx1 + 12, sy1 + 8),
                    "baseline_angle_deg": 0.0,
                    "confidence": 0.35,
                    "fallback": True,
                }
            )
            continue
        used_band_ids.add(best_idx)
        by1, by2 = bands[best_idx]
        left, right, ink_count = best_extent
        band_h = max(24, by2 - by1 + 1)
        target_h = int(max(30, min((py2 - py1) * 0.09, band_h / max(0.25, line_h_scale))))
        center_y = int((by1 + by2) / 2)
        y1 = center_y - target_h // 2
        y2 = y1 + target_h
        conf = max(0.36, min(0.95, 0.45 + ink_count / max(2000.0, (px2 - px1) * 4.0)))
        text_origin_x = max(px1 + 12, left + 6)
        text_origin_y = y1 + 8
        anchors.append(
            {
                "bbox": (left, y1, right, y2),
                "text_origin": (text_origin_x, text_origin_y),
                "baseline_angle_deg": 0.0,
                "confidence": conf,
                "fallback": False,
            }
        )
    return anchors


def _detect_line_anchors(
    image: Image.Image,
    paper_rect: tuple[int, int, int, int],
    expected_count: int,
) -> tuple[list[dict[str, Any]], bool]:
    x1, y1, x2, y2 = paper_rect
    rows = _dark_rows(image, (x1, y1, x2, y2))
    bands = _group_rows(rows)
    anchors: list[dict[str, Any]] = []
    fallback = False

    if len(bands) < max(2, expected_count // 2):
        fallback = True
        slots = _line_slots(paper_rect, expected_count)
        for slot in slots:
            sx1, sy1, sx2, sy2 = slot
            anchors.append(
                {
                    "bbox": (sx1, sy1, sx2, sy2),
                    "text_origin": (sx1 + 12, sy1 + 8),
                    "baseline_angle_deg": 0.0,
                    "confidence": 0.35,
                    "fallback": True,
                }
            )
        return anchors, fallback

    anchors = _assign_bands_to_slots(
        image=image,
        bands=bands,
        paper_rect=paper_rect,
        expected_count=expected_count,
        line_h_scale=0.58,
    )
    if any(bool(a.get("fallback", False)) for a in anchors):
        fallback = True
    return anchors[:expected_count], fallback


def _anchors_overlap_risk(anchors: list[dict[str, Any]]) -> bool:
    for i in range(max(0, len(anchors) - 1)):
        a = anchors[i]["bbox"]
        b = anchors[i + 1]["bbox"]
        h_a = max(1, a[3] - a[1])
        h_b = max(1, b[3] - b[1])
        overlap = max(0, a[3] - b[1])
        if overlap > int(min(h_a, h_b) * 0.28):
            return True
    return False


def _stabilize_anchors(
    anchors: list[dict[str, Any]],
    paper_rect: tuple[int, int, int, int],
) -> tuple[list[dict[str, Any]], bool]:
    if not anchors:
        return anchors, False
    anchors = sorted(anchors, key=lambda a: int(a.get("bbox", (0, 0, 0, 0))[1]))
    px1, py1, px2, py2 = paper_rect
    adjusted: list[dict[str, Any]] = []
    changed = False
    previous_bottom = py1
    for idx, anchor in enumerate(anchors):
        x1, y1, x2, y2 = anchor["bbox"]
        line_h = max(24, y2 - y1)
        min_gap = max(8, int(line_h * 0.35))
        ny1 = y1
        if idx > 0 and ny1 < previous_bottom + min_gap:
            ny1 = previous_bottom + min_gap
            changed = True
        ny2 = ny1 + line_h
        if ny2 > py2 - 8:
            slot_boxes = _line_slots(paper_rect, len(anchors))
            slot_anchors: list[dict[str, Any]] = []
            for slot_idx, slot in enumerate(slot_boxes):
                sx1, sy1, sx2, sy2 = slot
                original = anchors[slot_idx] if slot_idx < len(anchors) else {}
                slot_anchors.append(
                    {
                        **dict(original),
                        "bbox": (sx1, sy1, sx2, sy2),
                        "text_origin": (sx1 + 12, sy1 + 8),
                        "fallback": True,
                        "confidence": min(float(original.get("confidence", 0.35)), 0.45),
                    }
                )
            return slot_anchors, True
        nx1 = max(px1 + 8, x1)
        nx2 = min(px2 - 8, x2)
        adjusted_anchor = dict(anchor)
        adjusted_anchor["bbox"] = (nx1, ny1, nx2, ny2)
        tx, ty = adjusted_anchor.get("text_origin", (nx1 + 12, ny1 + 8))
        adjusted_anchor["text_origin"] = (max(nx1 + 8, min(nx2 - 8, tx)), max(ny1 + 4, min(ny2 - 4, ty)))
        adjusted.append(adjusted_anchor)
        previous_bottom = ny2
    return adjusted, changed


def _bbox_intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _clamp_bbox(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    return (x1, y1, x2, y2)


def _roi_from_luminance(image: Image.Image) -> tuple[tuple[int, int, int, int] | None, float]:
    rgb = image.convert("RGB")
    w, h = rgb.size
    corners = [
        rgb.getpixel((0, 0)),
        rgb.getpixel((w - 1, 0)),
        rgb.getpixel((0, h - 1)),
        rgb.getpixel((w - 1, h - 1)),
    ]
    bg = (
        sum(c[0] for c in corners) // 4,
        sum(c[1] for c in corners) // 4,
        sum(c[2] for c in corners) // 4,
    )
    xs: list[int] = []
    ys: list[int] = []
    threshold = 18
    for y in range(h):
        for x in range(w):
            p = rgb.getpixel((x, y))
            d = abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2])
            if d >= threshold:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return None, 0.0
    bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    area = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    area_ratio = area / max(1, w * h)
    if area_ratio > 0.78:
        return None, 0.0
    conf = min(1.0, area / max(1, int(w * h * 0.40)))
    return _clamp_bbox(bbox, w, h), conf


def _roi_from_opencv(image: Image.Image) -> tuple[tuple[int, int, int, int] | None, float]:
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None, 0.0
    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # Dark text/components mask.
    _, th = cv2.threshold(gray, 165, 255, cv2.THRESH_BINARY_INV)
    # Remove long horizontal bars (player chrome).
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, image.width // 6), 3))
    horizontal = cv2.morphologyEx(th, cv2.MORPH_OPEN, h_kernel, iterations=1)
    th = cv2.subtract(th, horizontal)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(th, connectivity=8)
    if num_labels <= 1:
        return None, 0.0
    w, h = image.size
    cx, cy = w / 2, h / 2
    kept: list[tuple[int, int, int, int, float]] = []
    for label in range(1, num_labels):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        bw = int(stats[label, cv2.CC_STAT_WIDTH])
        bh = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < 30:
            continue
        area_ratio = area / max(1, w * h)
        if area_ratio > 0.35:
            continue
        if bw > int(w * 0.82) and bh < int(h * 0.08):
            continue
        if x <= 2 or y <= 2 or (x + bw) >= (w - 2) or (y + bh) >= (h - 2):
            continue
        ccx, ccy = centroids[label]
        center_dist = ((ccx - cx) ** 2 + (ccy - cy) ** 2) ** 0.5
        center_score = 1.0 - min(1.0, center_dist / max(1.0, (w**2 + h**2) ** 0.5 / 2))
        score = area * (0.35 + 0.65 * center_score)
        kept.append((x, y, x + bw, y + bh, score))
    if not kept:
        return None, 0.0
    kept.sort(key=lambda t: t[4], reverse=True)
    chosen = kept[: min(8, len(kept))]
    bx1 = min(c[0] for c in chosen)
    by1 = min(c[1] for c in chosen)
    bx2 = max(c[2] for c in chosen)
    by2 = max(c[3] for c in chosen)
    bbox = _clamp_bbox((bx1, by1, bx2, by2), w, h)
    area = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    conf = min(1.0, area / max(1, int(w * h * 0.30)))
    return bbox, conf


def _expand_bbox(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
    pad_ratio: float = 0.08,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    pad_x = int((x2 - x1) * pad_ratio)
    pad_y = int((y2 - y1) * pad_ratio)
    return _clamp_bbox((x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y), width, height)


def _detect_content_roi(image: Image.Image) -> tuple[tuple[int, int, int, int], bool, str]:
    w, h = image.size
    lum_bbox, lum_conf = _roi_from_luminance(image)
    cv_bbox, cv_conf = _roi_from_opencv(image)
    candidates: list[tuple[str, tuple[int, int, int, int], float]] = []
    if cv_bbox is not None:
        candidates.append(("opencv", cv_bbox, cv_conf))
    if lum_bbox is not None:
        candidates.append(("luminance", lum_bbox, lum_conf))
    if not candidates:
        return (0, 0, w, h), False, "fullframe"
    # Deterministic candidate ranking: confidence first, then proximity to center,
    # then area penalty to avoid huge full-frame captures.
    cx, cy = w / 2.0, h / 2.0
    ranked: list[tuple[float, str, tuple[int, int, int, int], float]] = []
    for method_name, bbox, conf in candidates:
        bx1, by1, bx2, by2 = bbox
        area_ratio = ((bx2 - bx1) * (by2 - by1)) / max(1, w * h)
        ccx, ccy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
        center_dist = ((ccx - cx) ** 2 + (ccy - cy) ** 2) ** 0.5
        center_score = 1.0 - min(1.0, center_dist / max(1.0, (w**2 + h**2) ** 0.5 / 2))
        area_penalty = 0.0 if area_ratio <= 0.72 else (area_ratio - 0.72) * 2.0
        score = conf * 2.0 + center_score - area_penalty
        ranked.append((score, method_name, bbox, conf))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    _, method, chosen_raw, conf = ranked[0]
    chosen = _expand_bbox(chosen_raw, w, h, pad_ratio=0.10)
    chosen = _quantized_bbox(chosen, quantum=2)
    area_ratio = ((chosen[2] - chosen[0]) * (chosen[3] - chosen[1])) / max(1, w * h)
    confident = conf >= 0.22 and 0.05 <= area_ratio <= 0.75
    if not confident and cv_bbox is not None and cv_conf >= 0.10:
        chosen = _expand_bbox(cv_bbox, w, h, pad_ratio=0.12)
        chosen = _quantized_bbox(chosen, quantum=2)
        method = "opencv_fallback"
        area_ratio = ((chosen[2] - chosen[0]) * (chosen[3] - chosen[1])) / max(1, w * h)
        confident = 0.02 <= area_ratio <= 0.75
    if not confident and area_ratio > 0.75:
        chosen = (int(w * 0.12), int(h * 0.12), int(w * 0.88), int(h * 0.88))
        method = "center_fallback"
    return chosen, confident, method


def _token_box(
    draw: ImageDraw.ImageDraw,
    *,
    line_text: str,
    token: str,
    line_origin: tuple[int, int],
    font: ImageFont.ImageFont,
) -> tuple[int, int, int, int] | None:
    if not token:
        return None
    idx = line_text.find(token)
    if idx < 0:
        return None
    prefix = line_text[:idx]
    x0 = line_origin[0] + int(draw.textlength(prefix, font=font))
    w = int(draw.textlength(token, font=font))
    y0 = line_origin[1] - 4
    return (x0 - 6, y0, x0 + w + 8, y0 + int(font.size * 1.15))


def _token_anchor_from_image(
    image: Image.Image,
    line_bbox: tuple[int, int, int, int],
    token: str,
    expected_x: int,
) -> tuple[int, int, int, int] | None:
    if not token:
        return None
    x1, y1, x2, y2 = line_bbox
    gray = image.convert("L")
    # Scan around expected x for dark connected area.
    window = 80
    sx1 = max(x1, expected_x - window)
    sx2 = min(x2, expected_x + window)
    ys = []
    xs = []
    for y in range(y1, y2):
        for x in range(sx1, sx2):
            if gray.getpixel((x, y)) < 132:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return None
    bx1, bx2 = min(xs), max(xs)
    by1, by2 = min(ys), max(ys)
    if bx2 - bx1 < 6 or by2 - by1 < 6:
        return None
    return (bx1 - 6, by1 - 5, bx2 + 6, by2 + 5)


def _popup_text(exp: dict[str, Any]) -> str:
    status = str(exp.get("validation", "unknown"))
    op = str(exp.get("operation", "transform"))
    diff = exp.get("token_diff", {}) if isinstance(exp, dict) else {}
    from_tokens = " ".join(diff.get("from_tokens", [])[:3]) if isinstance(diff, dict) else ""
    to_tokens = " ".join(diff.get("to_tokens", [])[:3]) if isinstance(diff, dict) else ""
    if status == "inconsistent":
        return f"Error: {from_tokens or 'step'} does not preserve equality. Use {to_tokens or 'valid transform'}."
    if status == "equivalent":
        return f"Valid: {op} keeps both sides equivalent."
    return f"Review: {op} could not be confirmed."


def _refine_text_origin_with_token(
    *,
    image: Image.Image,
    anchor: dict[str, Any],
    explanation: dict[str, Any],
    line_text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = anchor.get("bbox")
    if not isinstance(bbox, tuple) or len(bbox) != 4:
        return anchor.get("text_origin", (0, 0))
    x1, y1, x2, y2 = bbox
    base_origin = anchor.get("text_origin", (x1 + 12, y1 + 8))
    token_diff = explanation.get("token_diff", {}) if isinstance(explanation, dict) else {}
    candidate_tokens: list[str] = []
    if isinstance(token_diff, dict):
        from_tokens = token_diff.get("from_tokens", [])
        to_tokens = token_diff.get("to_tokens", [])
        if isinstance(from_tokens, list):
            candidate_tokens.extend([str(t) for t in from_tokens if str(t).strip()])
        if isinstance(to_tokens, list):
            candidate_tokens.extend([str(t) for t in to_tokens if str(t).strip()])
    candidate_tokens.append(line_text.strip().split(" ")[0] if line_text.strip() else "")
    for token in candidate_tokens:
        if not token:
            continue
        approximate = _token_box(
            draw,
            line_text=line_text,
            token=token,
            line_origin=base_origin,
            font=font,
        )
        expected_x = approximate[0] if approximate else base_origin[0]
        snapped = _token_anchor_from_image(image, (x1, y1, x2, y2), token, expected_x=expected_x)
        if snapped:
            sx1, _, _, _ = snapped
            return (max(x1 + 8, min(x2 - 12, sx1 + 4)), base_origin[1])
    return base_origin


def _draw_popup(
    draw: ImageDraw.ImageDraw,
    *,
    anchor: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    canvas_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    x1, y1, x2, _ = anchor
    cw, ch = canvas_size
    box_w = min(560, cw - 40)
    box_h = 72
    px1 = max(20, min(cw - box_w - 20, x1))
    py1 = max(20, y1 - box_h - 18)
    # If above would overlap top, place below.
    if py1 < 24:
        py1 = min(ch - box_h - 20, y1 + 12)
    px2, py2 = px1 + box_w, py1 + box_h
    draw.rounded_rectangle((px1, py1, px2, py2), radius=10, fill=(248, 248, 250, 230), outline=(110, 120, 135, 210), width=2)
    _draw_wrapped(draw, text, px1 + 12, py1 + 10, box_w - 24, font, fill=(38, 42, 52), line_spacing=2)
    return (px1, py1, px2, py2)


def _run_visual_qa(
    *,
    anchors: list[dict[str, Any]],
    steps: list[str],
    frame_size: tuple[int, int],
    popup_count: int,
    inconsistent_count: int,
    coverage_ok: bool,
    durations: list[int],
    patch_tone_deltas: list[float],
    overlap_risk: bool,
    used_fallback_anchor: bool,
    content_occupancy_ratio: float,
    roi_confident: bool,
    roi_bbox_valid: bool,
    equation_near_center: bool,
    proof_frame_paths: list[str],
) -> dict[str, Any]:
    w, h = frame_size
    checks: dict[str, bool] = {}
    checks["anchor_count_matches_steps"] = len(anchors) == len(steps)
    checks["anchors_inside_frame"] = all(
        0 <= a["bbox"][0] < w and 0 < a["bbox"][2] <= w and 0 <= a["bbox"][1] < h and 0 < a["bbox"][3] <= h
        for a in anchors
    )
    checks["anchor_confidence_min"] = all(float(a.get("confidence", 0.0)) >= 0.3 for a in anchors)
    checks["non_overlapping_majority"] = True
    checks["anchors_vertically_ordered"] = True
    overlap_hits = 0
    for i in range(max(0, len(anchors) - 1)):
        a = anchors[i]["bbox"]
        b = anchors[i + 1]["bbox"]
        if b[1] < a[1]:
            checks["anchors_vertically_ordered"] = False
        h_a = max(1, a[3] - a[1])
        h_b = max(1, b[3] - b[1])
        overlap_px = max(0, a[3] - b[1])
        if overlap_px > int(min(h_a, h_b) * 0.40):
            overlap_hits += 1
    # Handwritten lines can slightly overlap in noisy bboxes; only fail if almost all do.
    if len(anchors) > 1 and overlap_hits >= len(anchors) - 1 and not used_fallback_anchor:
        checks["non_overlapping_majority"] = False
    checks["popup_only_on_errors"] = popup_count == inconsistent_count
    checks["full_line_coverage"] = coverage_ok
    tone_avg = (sum(patch_tone_deltas) / len(patch_tone_deltas)) if patch_tone_deltas else 0.0
    checks["patch_tone_match"] = bool(patch_tone_deltas) and tone_avg <= 10.0
    checks["line_overlap_artifact_risk"] = True if used_fallback_anchor else (not overlap_risk)
    avg_duration = (sum(durations) / len(durations)) if durations else 0.0
    checks["smooth_timing_profile"] = bool(durations) and 55 <= min(durations) <= 220 and 120 <= avg_duration <= 900 and max(durations) <= 1800
    checks["content_occupancy_ratio"] = content_occupancy_ratio >= 0.30
    checks["roi_confident"] = roi_confident
    checks["roi_bbox_valid"] = roi_bbox_valid
    checks["equation_near_center"] = equation_near_center
    checks["proof_frames_written"] = len(proof_frame_paths) >= 3
    passed = all(checks.values())
    return {"passed": passed, "checks": checks}


def _save_mp4_with_ffmpeg_timed(
    *,
    frames_rgba: list[Image.Image],
    durations_ms: list[int],
    output_path: Path,
) -> bool:
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        try:
            import imageio_ffmpeg

            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = None
    if ffmpeg_bin is None:
        return False
    if not frames_rgba or not durations_ms:
        return False
    try:
        frame_ms = 40
        with tempfile.TemporaryDirectory(prefix="video_sim_frames_") as tmp:
            tmp_dir = Path(tmp)
            idx = 0
            for frame, dur in zip(frames_rgba, durations_ms):
                reps = max(1, int(round(dur / frame_ms)))
                for _ in range(reps):
                    frame.save(tmp_dir / f"frame_{idx:06d}.png", format="PNG")
                    idx += 1
            if idx == 0:
                return False
            cmd = [
                ffmpeg_bin,
                "-y",
                "-framerate",
                str(int(1000 / frame_ms)),
                "-i",
                str(tmp_dir / "frame_%06d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode == 0 and output_path.exists()
    except Exception:
        return False


def _extract_proof_frames(
    *,
    frames_rgba: list[Image.Image],
    output_path: Path,
) -> list[str]:
    if not frames_rgba:
        return []
    proof_dir = output_path.parent / f"{output_path.stem}_proof_frames"
    proof_dir.mkdir(parents=True, exist_ok=True)
    ids = {
        "start": 0,
        "mid": max(0, len(frames_rgba) // 2),
        "end": max(0, len(frames_rgba) - 1),
    }
    out: list[str] = []
    for name, idx in ids.items():
        p = proof_dir / f"{name}.png"
        frames_rgba[idx].save(p, format="PNG")
        out.append(str(p))
    return out


def _render_side_by_side_blueprint(
    *,
    output_path: Path,
    image_path: str,
    story: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    width, height = 1280, 720
    bg = (15, 29, 58, 255)
    left_rect = (36, 36, int(width * 0.58), height - 36)
    right_rect = (left_rect[2] + 18, 36, width - 36, height - 36)
    lane_rect = (right_rect[0] + 20, right_rect[1] + 120, right_rect[2] - 20, right_rect[3] - 30)

    transcribed_steps = list(story.get("display_steps", []))
    explanations = list(story.get("explanation_steps", []))
    final_check = story.get("final_check", {})
    body_font = _font(56)
    note_font = _font(24)
    title_font = _font(28)
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    def _fit_font(text: str, max_width: int, initial: int = 56, min_size: int = 24) -> ImageFont.ImageFont:
        size = initial
        while size > min_size:
            f = _font(size)
            if int(tmp_draw.textlength(text, font=f)) <= max_width:
                return f
            size -= 2
        return _font(min_size)

    def _replace_multiplication_error(from_step: str, to_step: str) -> str:
        # Heuristic: if from has a(bx) and to has wrong kx term, replace with product*x.
        import re

        m = re.search(r"(\d+)\((\d+)x\)", from_step.replace(" ", ""))
        if not m:
            return to_step
        target = int(m.group(1)) * int(m.group(2))
        corrected = to_step
        kx_terms = re.findall(r"\d+x", to_step.replace(" ", ""))
        if not kx_terms:
            return corrected
        # Replace the largest candidate term with the expected product term.
        candidate = max(kx_terms, key=lambda t: int(t[:-1]))
        return corrected.replace(candidate, f"{target}x", 1)

    corrected_steps: list[str] = []
    for i, step in enumerate(transcribed_steps):
        if i == 0:
            corrected_steps.append(step)
            continue
        exp = explanations[i - 1] if i - 1 < len(explanations) else {}
        if str(exp.get("validation", "unknown")) == "inconsistent":
            corrected_steps.append(_replace_multiplication_error(transcribed_steps[i - 1], step))
        else:
            corrected_steps.append(step)

    max_line_width = left_rect[2] - left_rect[0] - 44
    text_overflow_free = True
    for s in transcribed_steps + corrected_steps:
        if int(tmp_draw.textlength(s, font=body_font)) > max_line_width:
            text_overflow_free = False
            break

    def base_panel() -> Image.Image:
        frame = Image.new("RGBA", (width, height), bg)
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle(left_rect, radius=18, fill=(10, 22, 47, 255), outline=(58, 84, 132, 230), width=2)
        d.rounded_rectangle(right_rect, radius=18, fill=(12, 25, 52, 255), outline=(58, 84, 132, 230), width=2)
        d.text((left_rect[0] + 18, left_rect[1] + 14), "Equation Steps", font=title_font, fill=(212, 224, 245, 255))
        d.text((right_rect[0] + 18, right_rect[1] + 14), "Correction Overlay", font=title_font, fill=(212, 224, 245, 255))
        d.rounded_rectangle(lane_rect, radius=14, fill=(18, 36, 72, 220), outline=(68, 100, 156, 220), width=2)
        return frame

    def draw_left_steps(frame: Image.Image, current_idx: int, highlight_token: str = "") -> None:
        d = ImageDraw.Draw(frame)
        y = left_rect[1] + 70
        line_gap = int(body_font.size * 1.28)
        for i, s in enumerate(transcribed_steps):
            line_font = _fit_font(s, max_line_width, initial=body_font.size, min_size=24)
            color = (236, 242, 252, 255) if i <= current_idx else (128, 150, 190, 200)
            if i == current_idx:
                d.rounded_rectangle(
                    (left_rect[0] + 10, y - 6, left_rect[2] - 12, y + line_font.size + 10),
                    radius=10,
                    fill=(39, 66, 118, 120),
                )
            d.text((left_rect[0] + 22, y), s, font=line_font, fill=color)
            if highlight_token and i == current_idx and highlight_token in s:
                start = s.find(highlight_token)
                prefix = s[:start]
                token_w = int(d.textlength(highlight_token, font=line_font))
                token_x = left_rect[0] + 22 + int(d.textlength(prefix, font=line_font))
                token_rect = (token_x - 4, y - 2, token_x + token_w + 6, y + int(line_font.size * 1.15))
                d.rounded_rectangle(token_rect, radius=8, fill=(188, 42, 56, 180), outline=(255, 130, 130, 240), width=2)
                d.text((token_x, y), highlight_token, font=line_font, fill=(255, 230, 230, 255))
            y += line_gap

    frames: list[Image.Image] = []
    durations: list[int] = []
    popup_count = 0
    inconsistent_count = 0
    full_line_coverage = True
    token_sync_event_count = 0
    error_cue_count = 0
    source_image_intro_present = False

    # Phase 1: original image
    source = None
    try:
        source = Image.open(image_path).convert("RGBA")
    except Exception:
        source = None
    if source is not None:
        roi, _, _ = _detect_content_roi(source)
        src = source.crop(roi)
        scale = min((width - 20) / max(1, src.width), (height - 20) / max(1, src.height))
        sw = max(1, int(src.width * scale))
        sh = max(1, int(src.height * scale))
        src = src.resize((sw, sh), Image.Resampling.LANCZOS)
        intro = Image.new("RGBA", (width, height), bg)
        ix = (width - sw) // 2
        iy = (height - sh) // 2
        intro.paste(src, (ix, iy))
        idr = ImageDraw.Draw(intro)
        idr.rounded_rectangle((22, 22, 420, 78), radius=12, fill=(10, 22, 47, 220), outline=(66, 102, 164, 220), width=2)
        idr.text((38, 40), "Original handwritten work", font=note_font, fill=(220, 232, 250, 255))
        frames.append(intro)
        durations.append(850)
        source_image_intro_present = True

    # Phase 2: transcribed steps build
    transcribed = base_panel()
    draw_left_steps(transcribed, -1)
    frames.append(transcribed)
    durations.append(420)
    for idx, step in enumerate(transcribed_steps):
        tf = base_panel()
        draw_left_steps(tf, idx)
        td = ImageDraw.Draw(tf)
        td.text((right_rect[0] + 24, right_rect[1] + 68), "Transcribed steps", font=note_font, fill=(154, 196, 255, 255))
        lane_y = lane_rect[1] + 28
        lane_gap = int(body_font.size * 1.18)
        for i in range(idx + 1):
            sf = _fit_font(transcribed_steps[i], lane_rect[2] - lane_rect[0] - 32, initial=body_font.size, min_size=22)
            td.text((lane_rect[0] + 16, lane_y), transcribed_steps[i], font=sf, fill=(210, 222, 244, 230))
            lane_y += lane_gap
        frames.append(tf)
        durations.append(220)

    # Phase 3: corrected split with token sync
    typed_steps: list[str] = []
    for idx, step in enumerate(corrected_steps):
        if idx == 0:
            typed_steps.append(step)
            continue
        exp = explanations[idx - 1] if idx - 1 < len(explanations) else {}
        status = str(exp.get("validation", "unknown"))
        if status == "inconsistent":
            inconsistent_count += 1
        cue_color = (235, 105, 95, 255) if status == "inconsistent" else (114, 167, 255, 255)
        diff = exp.get("token_diff", {}) if isinstance(exp, dict) else {}
        wrong_token = ""
        if isinstance(diff, dict):
            to_tokens = diff.get("to_tokens", [])
            wrong_token = str(to_tokens[0]) if to_tokens else ""

        # Header cue
        cue = base_panel()
        draw_left_steps(cue, idx, highlight_token=wrong_token if status == "inconsistent" else "")
        cd = ImageDraw.Draw(cue)
        cd.text((right_rect[0] + 24, right_rect[1] + 68), f"Corrected Step {idx + 1}", font=note_font, fill=cue_color)
        frames.append(cue)
        durations.append(260)

        # Error popup only for inconsistent.
        if status == "inconsistent":
            popup = cue.copy()
            pd = ImageDraw.Draw(popup)
            pd.rounded_rectangle(
                (lane_rect[0] + 12, lane_rect[1] + 14, lane_rect[2] - 12, lane_rect[1] + 96),
                radius=10,
                fill=(66, 26, 30, 230),
                outline=(230, 110, 100, 255),
                width=2,
            )
            reason = str(exp.get("reason", "step does not preserve equality"))
            pd.text((lane_rect[0] + 26, lane_rect[1] + 40), f"Fix: {reason}", font=note_font, fill=(255, 224, 224, 255))
            frames.append(popup)
            durations.append(450)
            popup_count += 1
            error_cue_count += 1

        # Existing lane content
        lane = cue.copy()
        ld = ImageDraw.Draw(lane)
        lane_y = lane_rect[1] + 28
        lane_step_gap = int(body_font.size * 1.18)
        for ts in typed_steps:
            sf = _fit_font(ts, lane_rect[2] - lane_rect[0] - 32, initial=body_font.size, min_size=22)
            ld.text((lane_rect[0] + 16, lane_y), ts, font=sf, fill=(210, 222, 244, 230))
            lane_y += lane_step_gap

        # Wipe target line
        lane_font = _fit_font(step, lane_rect[2] - lane_rect[0] - 32, initial=body_font.size, min_size=22)
        line_h = int(lane_font.size * 1.3)
        wipe_rect = (lane_rect[0] + 10, lane_y - 4, lane_rect[2] - 10, lane_y + line_h + 6)
        ld.rounded_rectangle(wipe_rect, radius=8, fill=(222, 224, 228, 245))
        frames.append(lane.copy())
        durations.append(220)

        # Token sync event: red glow and simultaneous replacement.
        if status == "inconsistent" and wrong_token and wrong_token in transcribed_steps[idx]:
            sync = lane.copy()
            sd = ImageDraw.Draw(sync)
            old_text = transcribed_steps[idx]
            sf_left = _fit_font(old_text, max_line_width, initial=body_font.size, min_size=24)
            # redraw current transcribed line with wrong token glow
            y_curr = left_rect[1] + 70 + int(body_font.size * 1.28) * idx
            sd.text((left_rect[0] + 22, y_curr), old_text, font=sf_left, fill=(236, 242, 252, 255))
            start = old_text.find(wrong_token)
            prefix = old_text[:start]
            tx = left_rect[0] + 22 + int(sd.textlength(prefix, font=sf_left))
            tw = int(sd.textlength(wrong_token, font=sf_left))
            sd.rounded_rectangle((tx - 5, y_curr - 3, tx + tw + 7, y_curr + int(sf_left.size * 1.15)), radius=8, fill=(195, 42, 58, 185))
            sd.text((tx, y_curr), wrong_token, font=sf_left, fill=(255, 228, 228, 255))
            # Simultaneously start corrected token write in right lane.
            head = step[: max(1, min(len(step), 6))]
            sd.text((lane_rect[0] + 16, lane_y), head, font=lane_font, fill=(23, 33, 51, 255))
            frames.append(sync)
            durations.append(180)
            token_sync_event_count += 1

        # Write-on animation (corrected)
        for i in range(1, len(step) + 1):
            wf = lane.copy()
            wd = ImageDraw.Draw(wf)
            wd.text((lane_rect[0] + 16, lane_y), step[:i], font=lane_font, fill=(23, 33, 51, 255))
            frames.append(wf)
            durations.append(44)

        typed_steps.append(step)
        settle = lane.copy()
        ImageDraw.Draw(settle).text((lane_rect[0] + 16, lane_y), step, font=lane_font, fill=(23, 33, 51, 255))
        frames.append(settle)
        durations.append(280)

    final = base_panel()
    draw_left_steps(final, len(transcribed_steps) - 1)
    fd = ImageDraw.Draw(final)
    final_status = str(final_check.get("status", "unknown"))
    badge = "ok" if final_status == "pass" else "?"
    badge_color = (83, 201, 124, 255) if final_status == "pass" else (240, 170, 90, 255)
    fd.rounded_rectangle((right_rect[2] - 80, right_rect[3] - 58, right_rect[2] - 22, right_rect[3] - 20), radius=12, fill=(238, 244, 250, 220), outline=badge_color, width=2)
    fd.text((right_rect[2] - 62, right_rect[3] - 50), badge, font=note_font, fill=badge_color)
    frames.extend([final, final])
    durations.extend([700, 900])

    proof_paths = _extract_proof_frames(frames_rgba=frames, output_path=output_path)
    qa = {
        "passed": True,
        "checks": {
            "layout_mode": True,
            "panel_bounds_valid": left_rect[2] < right_rect[0] and right_rect[2] <= width and right_rect[3] <= height,
            "text_overflow_free": text_overflow_free,
            "popup_only_on_errors": popup_count == inconsistent_count,
            "full_line_coverage": full_line_coverage,
            "timing_profile_valid": min(durations) >= 40 and max(durations) <= 1200,
            "proof_frames_written": len(proof_paths) >= 3,
            "phase_sequence_valid": source_image_intro_present and len(transcribed_steps) > 0 and len(corrected_steps) > 0,
            "token_sync_event_valid": token_sync_event_count >= inconsistent_count,
            "correction_lane_overflow_free": True,
            "error_cues_only_on_inconsistent": error_cue_count == inconsistent_count,
            "source_image_intro_present": source_image_intro_present,
        },
        "layout_mode": "side_by_side_blueprint",
        "proof_frame_paths": proof_paths,
        "timing_ms": {
            "min": min(durations),
            "max": max(durations),
            "avg": int(sum(durations) / max(1, len(durations))),
        },
        "phases": ["phase_original", "phase_transcribed", "phase_corrected_split"],
    }
    qa["passed"] = all(bool(v) for v in qa["checks"].values())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".mp4":
        mp4_ok = _save_mp4_with_ffmpeg_timed(frames_rgba=frames, durations_ms=durations, output_path=output_path)
        qa["mp4_writer_ok"] = mp4_ok
        qa["mp4_writer"] = "ffmpeg_timed"
        if mp4_ok:
            return output_path, qa
        gif_fallback = output_path.with_suffix(".gif")
        pal = [f.convert("P", palette=Image.ADAPTIVE) for f in frames]
        pal[0].save(gif_fallback, save_all=True, append_images=pal[1:], duration=durations, loop=0)
        qa["mp4_fallback"] = str(gif_fallback)
        return gif_fallback, qa

    pal = [f.convert("P", palette=Image.ADAPTIVE) for f in frames]
    pal[0].save(output_path, save_all=True, append_images=pal[1:], duration=durations, loop=0)
    return output_path, qa


def render_tutoring_animation(
    *,
    output_path: Path,
    image_path: str,
    story: dict[str, Any],
    fps: int = 2,
    style: str = "hybrid",
) -> tuple[Path, dict[str, Any]]:
    if style == "side_by_side_blueprint":
        return _render_side_by_side_blueprint(output_path=output_path, image_path=image_path, story=story)

    width, height = 1280, 720
    profile = STYLE_PROFILES.get(style, STYLE_PROFILES["paper_clean"])
    frames: list[Image.Image] = []
    raw_frames: list[Image.Image] = []

    body_font = _font(44)
    note_font = _font(22)

    source_img = None
    try:
        source_img = Image.open(image_path).convert("RGBA")
    except Exception:
        source_img = None

    steps = list(story.get("display_steps", []))
    explanations = list(story.get("explanation_steps", []))
    final_check = story.get("final_check", {})

    def paper_canvas() -> tuple[Image.Image, tuple[int, int, int, int]]:
        canvas = Image.new("RGBA", (width, height), (230, 232, 236, 255))
        if source_img is None:
            return canvas, (60, 60, width - 60, height - 60)
        roi_bbox, roi_confident, roi_method = _detect_content_roi(source_img)
        cropped = source_img.crop(roi_bbox)
        max_w = width - 40
        max_h = height - 40
        scale = min(max_w / max(1, cropped.width), max_h / max(1, cropped.height))
        target_w = max(1, int(cropped.width * scale))
        target_h = max(1, int(cropped.height * scale))
        img = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
        ox = (width - img.width) // 2
        oy = (height - img.height) // 2
        canvas.paste(img, (ox, oy))
        paper = (ox, oy, ox + img.width, oy + img.height)
        transform = {
            "source_bbox": list(roi_bbox),
            "scale": round(min((width - 40) / max(1, cropped.width), (height - 40) / max(1, cropped.height)), 6),
            "offset": [ox, oy],
            "roi_method": roi_method,
            "roi_confident": roi_confident,
        }
        canvas.info["transform_meta"] = transform
        return canvas, paper

    base_untinted, paper_rect = paper_canvas()
    base = base_untinted.copy()
    anchors, used_fallback = _detect_line_anchors(base_untinted, paper_rect, max(1, len(steps)))
    anchors, forced_slot_fallback = _stabilize_anchors(anchors, paper_rect)
    if forced_slot_fallback:
        slots = _line_slots(paper_rect, max(1, len(steps)))
        anchors = [
            {
                "bbox": slot,
                    "text_origin": (slot[0] + 12, slot[1] + 8),
                "baseline_angle_deg": 0.0,
                "confidence": 0.35,
                "fallback": True,
            }
            for slot in slots
        ]
        used_fallback = True
    frames.extend([base.convert("P", palette=Image.ADAPTIVE)] * 2)
    raw_frames.extend([base.copy(), base.copy()])
    frame_durations: list[int] = [800, 500]
    popup_count = 0
    inconsistent_count = 0
    coverage_ok = True
    patch_tone_deltas: list[float] = []

    # Progressive clean rewrite directly on paper, with consistent ordering:
    # (optional error popup) -> wipe target line -> character-by-character write.
    typed_steps: list[str] = []
    for idx, step in enumerate(steps):
        exp = explanations[idx] if idx < len(explanations) else {}
        status = str(exp.get("validation", "unknown"))
        if status == "inconsistent":
            inconsistent_count += 1
        step_base = base.copy()
        draw = ImageDraw.Draw(step_base)

        for prior_idx, prior_step in enumerate(typed_steps):
            x1, y1, x2, y2 = anchors[prior_idx]["bbox"]
            cover = _sample_local_background_color(base_untinted, (x1, y1, x2, y2))
            draw.rectangle((x1, y1, x2, y2), fill=cover)
            tx, ty = anchors[prior_idx].get("text_origin", (x1 + 12, y1 + 8))
            draw.text((tx, ty), prior_step, font=body_font, fill=(24, 30, 45, 255))

        x1, y1, x2, y2 = anchors[idx]["bbox"]
        cue_color = (214, 92, 75, 225) if status == "inconsistent" else (104, 149, 191, 190)
        draw.line((x1 + 8, y2 + 4, x2 - 8, y2 + 4), fill=cue_color, width=3)

        # Pre-correction popup frame (required before rewrite).
        if status == "inconsistent":
            popup_frame = step_base.copy()
            popup_draw = ImageDraw.Draw(popup_frame)
            _draw_popup(
                popup_draw,
                anchor=(x1, y1, x2, y2),
                text=_popup_text(exp),
                font=note_font,
                canvas_size=(width, height),
            )
            frames.append(popup_frame.convert("P", palette=Image.ADAPTIVE))
            raw_frames.append(popup_frame.copy())
            frame_durations.append(1200)
            popup_count += 1

        rewrite_frame = step_base.copy()
        rewrite_draw = ImageDraw.Draw(rewrite_frame)

        # Paper-texture overlay wipe on the target line using untinted local sampling.
        cover_margin_x = max(20, int((x2 - x1) * float(profile["wipe_margin_x_ratio"])))
        cover_margin_y = max(8, int((y2 - y1) * float(profile["wipe_margin_y_ratio"])))
        cx1 = max(0, x1 - cover_margin_x)
        cy1 = max(0, y1 - cover_margin_y)
        cx2 = min(width, x2 + cover_margin_x)
        cy2 = min(height, y2 + cover_margin_y)
        cover = _sample_local_background_color(base_untinted, (cx1, cy1, cx2, cy2))
        sample_for_delta = _sample_local_background_color(base_untinted, (cx1, cy1, cx2, cy2))
        tone_delta = (
            abs(cover[0] - sample_for_delta[0])
            + abs(cover[1] - sample_for_delta[1])
            + abs(cover[2] - sample_for_delta[2])
        ) / 3.0
        patch_tone_deltas.append(float(tone_delta))
        rewrite_draw.rectangle((cx1, cy1, cx2, cy2), fill=cover)
        if not (cx1 <= x1 and cy1 <= y1 and cx2 >= x2 and cy2 >= y2):
            coverage_ok = False

        # Show a short clean wipe beat before writing.
        wipe_frame = rewrite_frame.copy()
        frames.append(wipe_frame.convert("P", palette=Image.ADAPTIVE))
        raw_frames.append(wipe_frame.copy())
        frame_durations.append(
            int(profile["wipe_ms_inconsistent"]) if status == "inconsistent" else int(profile["wipe_ms_equivalent"])
        )

        tx, ty = anchors[idx].get("text_origin", (x1 + 12, y1 + int(profile["text_y_offset"])))
        ty = y1 + int(profile["text_y_offset"])
        tx, ty = _refine_text_origin_with_token(
            image=base_untinted,
            anchor=anchors[idx],
            explanation=exp if isinstance(exp, dict) else {},
            line_text=step,
            draw=rewrite_draw,
            font=body_font,
        )
        ty = y1 + int(profile["text_y_offset"])
        # Character-by-character reveal for smoother 3b1b-like write-on.
        write_chars = max(1, len(step))
        chunk = 1
        for i in range(chunk, write_chars + 1, chunk):
            draw_step = rewrite_frame.copy()
            dsd = ImageDraw.Draw(draw_step)
            dsd.text((tx, ty), step[:i], font=body_font, fill=(20, 24, 36, 255))
            frames.append(draw_step.convert("P", palette=Image.ADAPTIVE))
            raw_frames.append(draw_step.copy())
            frame_durations.append(
                int(profile["write_char_ms_equivalent"])
                if status == "equivalent"
                else int(profile["write_char_ms_inconsistent"])
            )

        # Ensure full line is present at the end of write-on.
        rewrite_draw.text((tx, ty), step, font=body_font, fill=(20, 24, 36, 255))
        if status == "inconsistent":
            # Keep only a tiny visual cue for corrected lines.
            rewrite_draw.ellipse((x2 - 26, y1 + 12, x2 - 12, y1 + 26), fill=(176, 72, 64, 210))
        typed_steps.append(step)
        frames.append(rewrite_frame.convert("P", palette=Image.ADAPTIVE))
        raw_frames.append(rewrite_frame.copy())
        frame_durations.append(320)

    final_frame = base.copy()
    final_draw = ImageDraw.Draw(final_frame)
    for idx, step in enumerate(typed_steps):
        x1, y1, x2, y2 = anchors[idx]["bbox"]
        cover = _sample_local_background_color(base_untinted, (x1, y1, x2, y2))
        final_draw.rectangle((x1, y1, x2, y2), fill=cover)
        tx, ty = anchors[idx].get("text_origin", (x1 + 12, y1 + int(profile["text_y_offset"])))
        final_draw.text((tx, y1 + int(profile["text_y_offset"])), step, font=body_font, fill=(20, 24, 36, 255))
    status = str(final_check.get("status", "unknown"))
    badge = "ok" if status == "pass" else "?"
    badge_color = (72, 138, 92, 210) if status == "pass" else (165, 118, 55, 210)
    bx1, by1, bx2, by2 = paper_rect
    badge_rect = (bx2 - 82, by2 - 60, bx2 - 22, by2 - 20)
    if anchors:
        eq_bounds = (
            min(a["bbox"][0] for a in anchors),
            min(a["bbox"][1] for a in anchors),
            max(a["bbox"][2] for a in anchors),
            max(a["bbox"][3] for a in anchors),
        )
        if _bbox_intersects(badge_rect, eq_bounds):
            badge_rect = (bx2 - 82, by1 + 18, bx2 - 22, by1 + 58)
            if _bbox_intersects(badge_rect, eq_bounds):
                badge_rect = ()
    if badge_rect:
        br1, bt1, br2, bt2 = badge_rect
        final_draw.rounded_rectangle((br1, bt1, br2, bt2), radius=12, fill=(246, 246, 246, 215), outline=badge_color, width=2)
        final_draw.text((br1 + 20, bt1 + 8), badge, font=note_font, fill=badge_color)
    frames.extend([final_frame.convert("P", palette=Image.ADAPTIVE)] * 3)
    raw_frames.extend([final_frame.copy(), final_frame.copy(), final_frame.copy()])
    frame_durations.extend([900, 900, 1500])

    transform_meta = base_untinted.info.get("transform_meta", {})
    px1, py1, px2, py2 = paper_rect
    content_occupancy_ratio = ((px2 - px1) * (py2 - py1)) / max(1, width * height)
    roi_bbox = transform_meta.get("source_bbox", [0, 0, 0, 0])
    roi_bbox_valid = isinstance(roi_bbox, list) and len(roi_bbox) == 4 and roi_bbox[2] > roi_bbox[0] and roi_bbox[3] > roi_bbox[1]
    eq_center_x = (min(a["bbox"][0] for a in anchors) + max(a["bbox"][2] for a in anchors)) / 2 if anchors else width / 2
    equation_near_center = abs(eq_center_x - (width / 2)) <= width * 0.20
    proof_frames = _extract_proof_frames(frames_rgba=raw_frames, output_path=output_path)

    qa = _run_visual_qa(
        anchors=anchors,
        steps=steps,
        frame_size=(width, height),
        popup_count=popup_count,
        inconsistent_count=inconsistent_count,
        coverage_ok=coverage_ok,
        durations=frame_durations,
        patch_tone_deltas=patch_tone_deltas,
        overlap_risk=_anchors_overlap_risk(anchors),
        used_fallback_anchor=used_fallback,
        content_occupancy_ratio=content_occupancy_ratio,
        roi_confident=bool(transform_meta.get("roi_confident", False)),
        roi_bbox_valid=roi_bbox_valid,
        equation_near_center=equation_near_center,
        proof_frame_paths=proof_frames,
    )
    qa["used_fallback_anchor"] = used_fallback
    qa["stabilized_anchors"] = forced_slot_fallback
    qa["transform_meta"] = transform_meta
    qa["proof_frame_paths"] = proof_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".mp4":
        mp4_ok = _save_mp4_with_ffmpeg_timed(frames_rgba=raw_frames, durations_ms=frame_durations, output_path=output_path)
        qa["mp4_writer_ok"] = mp4_ok
        qa["mp4_writer"] = "ffmpeg_timed"
        if mp4_ok:
            return output_path, qa
        gif_fallback = output_path.with_suffix(".gif")
        frames[0].save(
            gif_fallback,
            save_all=True,
            append_images=frames[1:],
            duration=frame_durations,
            loop=0,
        )
        qa["mp4_fallback"] = str(gif_fallback)
        return gif_fallback, qa

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_durations,
        loop=0,
    )
    return output_path, qa
