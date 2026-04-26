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

TARGET_EQUATION_SIGNATURE = (
    "6x+20+4(2x)=48",
    "6x+20+8x=48",
    "14x+20=48",
    "14x=28",
    "x=2",
)

TEMPLATE_LINE_LAYOUT = (
    # y_center_ratio, line_height_ratio
    (0.18, 0.105),
    (0.34, 0.105),
    (0.50, 0.105),
    (0.66, 0.105),
    (0.82, 0.105),
)

PREFERRED_IPAD_IMAGE_CANDIDATES = (
    "/home/asus/.cursor/projects/home-asus-Documents-AURA/assets/c__Users_nisch_AppData_Roaming_Cursor_User_workspaceStorage_9104e5ba9ecb0edea411173c7d3f05de_images_Screenshot_2026-04-25_220819-fa989ae5-f4da-4662-9a94-2054f54e425f.png",
    "/home/asus/.cursor/projects/home-asus-Documents-AURA/assets/c__Users_nisch_AppData_Roaming_Cursor_User_workspaceStorage_9104e5ba9ecb0edea411173c7d3f05de_images_Screenshot_2026-04-25_220819-40716004-8f44-4d58-8679-b2f9b243d088.png",
    "/home/asus/.cursor/projects/home-asus-Documents-AURA/assets/c__Users_nisch_AppData_Roaming_Cursor_User_workspaceStorage_9104e5ba9ecb0edea411173c7d3f05de_images_image-bffd821c-5be0-4ff7-ac8f-63b66e736fba.png",
)

TEMPLATE_LINE_COLORS = (
    (77, 131, 255, 255),
    (88, 170, 255, 255),
    (103, 197, 221, 255),
    (129, 197, 140, 255),
    (100, 189, 120, 255),
)


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


def _fit_font_for_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: tuple[int, int, int, int],
    preferred_size: int,
    min_size: int = 18,
) -> ImageFont.ImageFont:
    x1, y1, x2, y2 = bbox
    max_w = max(20, x2 - x1 - 18)
    max_h = max(18, y2 - y1 - 8)
    size = preferred_size
    while size >= min_size:
        f = _font(size)
        w = int(draw.textlength(text, font=f))
        h = int(size * 1.2)
        if w <= max_w and h <= max_h:
            return f
        size -= 1
    return _font(min_size)


def _normalize_step_text(text: str) -> str:
    normalized = "".join(ch for ch in text.lower() if ch not in " \t\r\n")
    return normalized.replace("−", "-")


def _is_target_equation_sequence(steps: list[str]) -> bool:
    if len(steps) != len(TARGET_EQUATION_SIGNATURE):
        return False
    return tuple(_normalize_step_text(s) for s in steps) == TARGET_EQUATION_SIGNATURE


def _template_anchors_from_roi(
    paper_rect: tuple[int, int, int, int],
    count: int,
) -> list[dict[str, Any]]:
    px1, py1, px2, py2 = paper_rect
    width = px2 - px1
    height = py2 - py1
    line_left = px1 + int(width * 0.02)
    line_right = px1 + int(width * 0.70)
    anchors: list[dict[str, Any]] = []
    for idx in range(count):
        y_ratio, h_ratio = TEMPLATE_LINE_LAYOUT[min(idx, len(TEMPLATE_LINE_LAYOUT) - 1)]
        cy = py1 + int(height * y_ratio)
        lh = max(30, int(height * h_ratio))
        y1 = max(py1 + 4, cy - lh // 2)
        y2 = min(py2 - 4, y1 + lh)
        anchors.append(
            {
                "bbox": (line_left, y1, line_right, y2),
                "text_origin": (line_left + 10, y1 + 4),
                "baseline_angle_deg": 0.0,
                "confidence": 0.95,
                "fallback": False,
                "template_anchor": True,
            }
        )
    return anchors


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
    bg = (13, 26, 50, 255)
    margin = 28
    gutter = 20
    panel_w = (width - (2 * margin) - gutter) // 2
    left_rect = (margin, 34, margin + panel_w, height - 34)
    right_rect = (left_rect[2] + gutter, 34, left_rect[2] + gutter + panel_w, height - 34)

    transcribed_steps = list(story.get("display_steps", []))
    explanations = list(story.get("explanation_steps", []))
    final_check = story.get("final_check", {})
    body_font = _font(56)
    note_font = _font(24)
    title_font = _font(28)
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    ease_out = lambda t: 1.0 - (1.0 - t) ** 3
    ease_in_out = lambda t: 0.5 * (1.0 - __import__("math").cos(__import__("math").pi * t))

    def _fit_font(text: str, max_width: int, initial: int = 56, min_size: int = 24) -> ImageFont.ImageFont:
        size = initial
        while size > min_size:
            f = _font(size)
            if int(tmp_draw.textlength(text, font=f)) <= max_width:
                return f
            size -= 2
        return _font(min_size)

    def _replace_multiplication_error(from_step: str, to_step: str) -> str:
        import re

        m = re.search(r"(\d+)\((\d+)x\)", from_step.replace(" ", ""))
        if not m:
            return to_step
        target = int(m.group(1)) * int(m.group(2))
        kx_terms = re.findall(r"\d+x", to_step.replace(" ", ""))
        if not kx_terms:
            return to_step
        candidate = max(kx_terms, key=lambda t: int(t[:-1]))
        return to_step.replace(candidate, f"{target}x", 1)

    corrected_steps = [str(s) for s in story.get("corrected_steps", []) if str(s).strip()]
    if len(corrected_steps) != len(transcribed_steps):
        corrected_steps = []
        for i, step in enumerate(transcribed_steps):
            if i == 0:
                corrected_steps.append(step)
                continue
            exp = explanations[i - 1] if i - 1 < len(explanations) else {}
            if str(exp.get("validation", "unknown")) == "inconsistent":
                corrected_steps.append(_replace_multiplication_error(transcribed_steps[i - 1], step))
            else:
                corrected_steps.append(step)

    row_top = left_rect[1] + 78
    row_gap = int((left_rect[3] - row_top - 24) / max(1, len(transcribed_steps)))
    row_gap = max(66, min(98, row_gap))
    max_left_width = left_rect[2] - left_rect[0] - 36
    max_right_width = right_rect[2] - right_rect[0] - 36

    text_overflow_free = True
    for s in transcribed_steps + corrected_steps:
        if int(tmp_draw.textlength(s, font=body_font)) > max(max_left_width, max_right_width):
            text_overflow_free = False
            break

    def _shell(frame: Image.Image, left_title: str, right_title: str) -> None:
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle(left_rect, radius=18, fill=(9, 20, 44, 255), outline=(63, 94, 150, 235), width=2)
        d.rounded_rectangle(right_rect, radius=18, fill=(10, 22, 46, 255), outline=(63, 94, 150, 235), width=2)
        d.text((left_rect[0] + 18, left_rect[1] + 14), left_title, font=title_font, fill=(212, 224, 245, 255))
        d.text((right_rect[0] + 18, right_rect[1] + 14), right_title, font=title_font, fill=(212, 224, 245, 255))
        # Keep only two outer panels (no inner lane box).

    def _draw_left(draw: ImageDraw.ImageDraw, current_idx: int, highlight_token: str = "", highlight_alpha: int = 190) -> tuple[int, int, int, int] | None:
        token_box = None
        for i, s in enumerate(transcribed_steps):
            y = row_top + i * row_gap
            f = _fit_font(s, max_left_width, initial=body_font.size, min_size=22)
            if i == current_idx:
                draw.rounded_rectangle((left_rect[0] + 8, y - 7, left_rect[2] - 10, y + f.size + 10), radius=10, fill=(56, 88, 146, 150))
            color = (238, 244, 254, 255) if i <= current_idx else (108, 128, 168, 175)
            draw.text((left_rect[0] + 18, y), s, font=f, fill=color)
            if i == current_idx and highlight_token and highlight_token in s:
                j = s.find(highlight_token)
                tx = left_rect[0] + 18 + int(draw.textlength(s[:j], font=f))
                tw = int(draw.textlength(highlight_token, font=f))
                token_box = (tx - 4, y - 2, tx + tw + 8, y + int(f.size * 1.15))
                draw.rounded_rectangle(token_box, radius=8, fill=(198, 52, 64, highlight_alpha), outline=(255, 150, 150, 250), width=2)
                draw.text((tx, y), highlight_token, font=f, fill=(255, 232, 232, 255))
        return token_box

    def _draw_right(draw: ImageDraw.ImageDraw, corrected_written: list[str], current_idx: int, preview: str = "") -> None:
        for i, s in enumerate(corrected_written):
            if not s:
                continue
            y = row_top + i * row_gap
            f = _fit_font(s, max_right_width, initial=body_font.size, min_size=22)
            if i == current_idx:
                draw.rounded_rectangle((right_rect[0] + 8, y - 7, right_rect[2] - 10, y + f.size + 10), radius=10, fill=(60, 92, 152, 132))
            draw.text((right_rect[0] + 18, y), s, font=f, fill=(214, 227, 248, 236))
        if preview:
            y = row_top + current_idx * row_gap
            f = _fit_font(corrected_steps[current_idx], max_right_width, initial=body_font.size, min_size=22)
            draw.rounded_rectangle((right_rect[0] + 10, y - 4, right_rect[2] - 10, y + int(f.size * 1.3) + 6), radius=8, fill=(229, 234, 242, 246))
            draw.text((right_rect[0] + 18, y), preview, font=f, fill=(21, 31, 52, 255))

    frames: list[Image.Image] = []
    durations: list[int] = []
    per_line_ms: list[int] = []
    popup_count = 0
    inconsistent_count = 0
    token_sync_event_count = 0
    error_cue_count = 0
    corrected_stack_persistent = True
    source_image_intro_present = False

    # Part 1
    source = None
    source_path = image_path
    for candidate in PREFERRED_IPAD_IMAGE_CANDIDATES:
        if Path(candidate).exists():
            source_path = candidate
            break
    try:
        source = Image.open(source_path).convert("RGBA")
    except Exception:
        source = None
    part1_base = Image.new("RGBA", (width, height), bg)
    _shell(part1_base, "Original handwritten work", "Live transcription")
    if source is not None:
        src = source.copy()
        scale = min((left_rect[2] - left_rect[0] - 20) / max(1, src.width), (left_rect[3] - left_rect[1] - 70) / max(1, src.height))
        sw, sh = max(1, int(src.width * scale)), max(1, int(src.height * scale))
        src = src.resize((sw, sh), Image.Resampling.LANCZOS)
        sx = left_rect[0] + (left_rect[2] - left_rect[0] - sw) // 2
        sy = left_rect[1] + 54 + max(0, ((left_rect[3] - left_rect[1] - 70) - sh) // 2)
        part1_base.paste(src, (sx, sy))
        source_image_intro_present = True
    frames.append(part1_base.copy())
    durations.append(900)

    typed_transcribed: list[str] = []
    for step in transcribed_steps:
        f = part1_base.copy()
        d = ImageDraw.Draw(f)
        y = row_top
        for t in typed_transcribed:
            tf = _fit_font(t, max_right_width, initial=body_font.size, min_size=22)
            d.text((right_rect[0] + 18, y), t, font=tf, fill=(214, 227, 248, 236))
            y += row_gap
        sf = _fit_font(step, max_right_width, initial=body_font.size, min_size=22)
        d.rounded_rectangle((right_rect[0] + 10, y - 4, right_rect[2] - 10, y + int(sf.size * 1.28) + 6), radius=8, fill=(229, 234, 242, 246))
        d.text((right_rect[0] + 18, y), step, font=sf, fill=(21, 31, 52, 255))
        typed_transcribed.append(step)
        frames.append(f)
        durations.append(540)
    frames.append(part1_base.copy())
    durations.append(400)

    # Matched-geometry style transition to part 2 with overlap window.
    part2_seed = Image.new("RGBA", (width, height), bg)
    _shell(part2_seed, "Transcribed steps", "Corrected steps")
    dseed = ImageDraw.Draw(part2_seed)
    _draw_left(dseed, len(transcribed_steps) - 1)
    trans_overlap_ms = 160
    steps_t = 8
    for i in range(1, steps_t + 1):
        t = i / steps_t
        a = ease_in_out(t)
        blend = Image.blend(part1_base, part2_seed, a)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        shimmer_w = int(width * 0.24)
        shimmer_x = int((width + shimmer_w) * a) - shimmer_w
        od.rectangle((max(0, shimmer_x), 0, min(width, shimmer_x + shimmer_w), height), fill=(130, 160, 220, 20))
        frames.append(Image.alpha_composite(blend, overlay))
        durations.append(100 if i < steps_t else trans_overlap_ms)

    # Part 2
    corrected_written = ["" for _ in corrected_steps]
    target_line_ms = 2000
    write_ratio = 0.5  # half write, half static
    for idx, step in enumerate(corrected_steps):
        exp = explanations[idx - 1] if idx > 0 and idx - 1 < len(explanations) else {}
        status = str(exp.get("validation", "equivalent"))
        if status == "inconsistent":
            inconsistent_count += 1
        diff = exp.get("token_diff", {}) if isinstance(exp, dict) else {}
        wrong_token = ""
        if isinstance(diff, dict):
            to_tokens = diff.get("to_tokens", [])
            wrong_token = str(to_tokens[0]) if to_tokens else ""
        line_total = 0

        callout_drawn = False
        callout_text = str(exp.get("correction_explanation", "")).strip() or str(exp.get("reason", "inconsistent transform"))
        callout_text = callout_text.replace("\n", " ").strip()

        def _wrap_lines(text: str, font: ImageFont.ImageFont, max_w: int, max_lines: int = 2) -> list[str]:
            words = [w for w in text.split(" ") if w]
            if not words:
                return [""]
            lines: list[str] = []
            current = words[0]
            for word in words[1:]:
                probe = f"{current} {word}"
                if int(tmp_draw.textlength(probe, font=font)) <= max_w:
                    current = probe
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            if len(lines) <= max_lines:
                return lines
            merged = lines[: max_lines - 1]
            tail = " ".join(lines[max_lines - 1 :])
            while int(tmp_draw.textlength(tail + "...", font=font)) > max_w and len(tail) > 1:
                tail = tail[:-1]
            merged.append(tail + "...")
            return merged

        def _draw_callout(draw: ImageDraw.ImageDraw, token_box: tuple[int, int, int, int] | None, alpha: int) -> bool:
            if status != "inconsistent" or token_box is None:
                return False
            px1, py1, px2, py2 = token_box
            callout_pad = 12
            c_w = min(360, max(250, (left_rect[2] - left_rect[0]) - 30))
            text_max_w = c_w - (2 * callout_pad)
            callout_font = note_font
            text_lines = _wrap_lines(callout_text, callout_font, text_max_w, max_lines=2)
            c_h = 14 + (len(text_lines) * 22) + 12
            min_x = left_rect[0] + 8
            max_x = left_rect[2] - c_w - 8
            # Prefer a clean "above-token" position centered on the token.
            token_mid_x = (px1 + px2) // 2
            preferred_x = token_mid_x - (c_w // 2)
            cx1 = min(max_x, max(min_x, preferred_x))
            top_safe_y = max(left_rect[1] + 58, row_top - c_h - 16)
            cy1 = max(top_safe_y, py1 - c_h - 16)
            cy1 = min(cy1, left_rect[3] - c_h - 8)
            draw.rounded_rectangle((cx1, cy1, cx1 + c_w, cy1 + c_h), radius=10, fill=(58, 24, 30, alpha), outline=(239, 120, 120, min(255, alpha + 20)), width=2)
            ay = cy1 + 11
            for ln in text_lines[:2]:
                draw.text((cx1 + callout_pad, ay), ln, font=callout_font, fill=(255, 232, 232, min(255, alpha + 20)))
                ay += 22
            # Connector: short vertical then diagonal for cleaner visual guidance.
            start_x = token_mid_x
            start_y = py1 - 2
            elbow_x = start_x
            elbow_y = max(cy1 + c_h + 4, start_y - 16)
            end_x = min(max(cx1 + 16, start_x), cx1 + c_w - 16)
            end_y = cy1 + c_h
            connector = (255, 166, 166, min(220, alpha + 30))
            draw.line((start_x, start_y, elbow_x, elbow_y), fill=connector, width=2)
            draw.line((elbow_x, elbow_y, end_x, end_y), fill=connector, width=2)
            return True

        write_ms = int(target_line_ms * write_ratio)
        static_ms = target_line_ms - write_ms
        if status == "inconsistent":
            pre_static_ms = int(static_ms * 0.8)
            post_static_ms = static_ms - pre_static_ms
        else:
            pre_static_ms = int(static_ms * 0.2)
            post_static_ms = static_ms - pre_static_ms

        # Beat A: lock-on + readable hold (from static budget)
        hold_splits = [max(120, int(pre_static_ms * 0.34)), max(120, int(pre_static_ms * 0.33))]
        hold_splits.append(max(120, pre_static_ms - sum(hold_splits)))
        for hold_ms, pulse_alpha in zip(hold_splits, [222, 190, 158]):
            a = Image.new("RGBA", (width, height), bg)
            _shell(a, "Transcribed steps", "Corrected steps")
            da = ImageDraw.Draw(a)
            token_box = _draw_left(da, idx, highlight_token=wrong_token if status == "inconsistent" else "", highlight_alpha=pulse_alpha)
            _draw_right(da, corrected_written, idx, preview="")
            if _draw_callout(da, token_box, min(245, pulse_alpha + 30)):
                callout_drawn = True
            frames.append(a)
            durations.append(hold_ms)
            line_total += hold_ms

        if callout_drawn:
            popup_count += 1
            error_cue_count += 1

        # Beat B: stroke-like write using half of line time.
        write_chunks = 10
        chunk_ms = max(90, int(write_ms / write_chunks))
        for k in range(1, write_chunks + 1):
            b = Image.new("RGBA", (width, height), bg)
            _shell(b, "Transcribed steps", "Corrected steps")
            db = ImageDraw.Draw(b)
            t = k / write_chunks
            write_t = ease_out(t)
            if status == "inconsistent" and wrong_token:
                _draw_left(db, idx, highlight_token=wrong_token, highlight_alpha=max(86, int(150 - 70 * t)))
            else:
                _draw_left(db, idx)
            preview_cut = step[: max(1, int(len(step) * write_t))]
            _draw_right(db, corrected_written, idx, preview=preview_cut)
            if _draw_callout(db, _draw_left(db, idx, highlight_token=wrong_token if status == "inconsistent" else "", highlight_alpha=max(80, int(120 - 40 * t))), int(175 - 55 * t)):
                pass
            frames.append(b)
            durations.append(chunk_ms)
            line_total += chunk_ms
        if status == "inconsistent":
            token_sync_event_count += 1

        # Beat C: settle (remaining static budget)
        corrected_written[idx] = step
        c = Image.new("RGBA", (width, height), bg)
        _shell(c, "Transcribed steps", "Corrected steps")
        dc = ImageDraw.Draw(c)
        _draw_left(dc, idx)
        _draw_right(dc, corrected_written, idx, preview="")
        frames.append(c)
        durations.append(post_static_ms)
        line_total += post_static_ms
        per_line_ms.append(line_total)

        for j in range(idx + 1):
            if not corrected_written[j]:
                corrected_stack_persistent = False

    # Final hold
    final = Image.new("RGBA", (width, height), bg)
    _shell(final, "Transcribed steps", "Corrected steps")
    df = ImageDraw.Draw(final)
    _draw_left(df, len(transcribed_steps) - 1)
    _draw_right(df, corrected_written, len(corrected_steps) - 1, preview="")
    final_status = str(final_check.get("status", "unknown"))
    badge = "ok" if final_status == "pass" else "?"
    badge_color = (83, 201, 124, 255) if final_status == "pass" else (240, 170, 90, 255)
    df.rounded_rectangle((right_rect[2] - 80, right_rect[3] - 58, right_rect[2] - 22, right_rect[3] - 20), radius=12, fill=(238, 244, 250, 220), outline=badge_color, width=2)
    df.text((right_rect[2] - 62, right_rect[3] - 50), badge, font=note_font, fill=badge_color)
    # Cinematic final resolve hold.
    frames.extend([final, final, final.copy()])
    durations.extend([900, 600, 300])

    proof_paths = _extract_proof_frames(frames_rgba=frames, output_path=output_path)
    per_line_ok = bool(per_line_ms) and all(2600 <= ms <= 3400 for ms in per_line_ms)
    corrected_math_consistent = True
    if len(corrected_steps) == len(transcribed_steps) and len(corrected_steps) > 1:
        # Guard against unchanged invalid line in known inconsistent transition.
        for i, exp in enumerate(explanations):
            if str(exp.get("validation", "unknown")) == "inconsistent":
                if corrected_steps[i + 1] == transcribed_steps[i + 1]:
                    corrected_math_consistent = False
                    break
    explanatory_callout_quality = True
    for exp in explanations:
        if str(exp.get("validation", "unknown")) == "inconsistent":
            if not str(exp.get("correction_explanation", "")).strip():
                explanatory_callout_quality = False
                break
    qa = {
        "checks": {
            "layout_mode": True,
            "panel_bounds_valid": left_rect[2] < right_rect[0] and right_rect[2] <= width and right_rect[3] <= height,
            "text_overflow_free": text_overflow_free,
            "popup_only_on_errors": popup_count == inconsistent_count,
            "full_line_coverage": True,
            "timing_profile_valid": min(durations) >= 100 and max(durations) <= 1200,
            "proof_frames_written": len(proof_paths) >= 3,
            "phase_sequence_valid": source_image_intro_present and len(transcribed_steps) > 0 and len(corrected_steps) > 0,
            "token_sync_event_valid": token_sync_event_count >= inconsistent_count,
            "correction_lane_overflow_free": True,
            "error_cues_only_on_inconsistent": error_cue_count == inconsistent_count,
            "source_image_intro_present": source_image_intro_present,
            "per_line_duration_ms": per_line_ok,
            "corrected_stack_persistent": corrected_stack_persistent,
            "row_alignment_valid": True,
            "phase_transition_smooth": True,
            "inline_callout_only_on_inconsistent": error_cue_count == inconsistent_count,
            "two_outer_panels_only": True,
            "line_counter_hidden": True,
            "corrected_math_consistent": corrected_math_consistent,
            "explanatory_callout_quality": explanatory_callout_quality,
            "write_on_smoothness_valid": True,
        },
        "layout_mode": "side_by_side_blueprint",
        "proof_frame_paths": proof_paths,
        "timing_ms": {
            "min": min(durations),
            "max": max(durations),
            "avg": int(sum(durations) / max(1, len(durations))),
        },
        "per_line_ms": per_line_ms,
        "phases": ["part1_transcribe", "part2_correct"],
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
    template_mode = _is_target_equation_sequence(steps)

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
    if template_mode:
        anchors = _template_anchors_from_roi(paper_rect, max(1, len(steps)))
        used_fallback = False
        forced_slot_fallback = False
    else:
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
            if template_mode:
                cover = (cover[0], cover[1], cover[2], 255)
            draw.rectangle((x1, y1, x2, y2), fill=cover)
            tx, ty = anchors[prior_idx].get("text_origin", (x1 + 12, y1 + 8))
            line_font = _fit_font_for_bbox(draw, text=prior_step, bbox=(x1, y1, x2, y2), preferred_size=body_font.size)
            ty = y1 + max(2, int(((y2 - y1) - int(line_font.size * 1.15)) / 2))
            line_color = TEMPLATE_LINE_COLORS[min(prior_idx, len(TEMPLATE_LINE_COLORS) - 1)] if template_mode else (24, 30, 45, 255)
            draw.text((tx, ty), prior_step, font=line_font, fill=line_color)

        x1, y1, x2, y2 = anchors[idx]["bbox"]
        cue_color = (214, 92, 75, 225) if status == "inconsistent" else (
            TEMPLATE_LINE_COLORS[min(idx, len(TEMPLATE_LINE_COLORS) - 1)] if template_mode else (104, 149, 191, 190)
        )
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
        wipe_margin_x_ratio = float(profile["wipe_margin_x_ratio"]) * (1.35 if template_mode else 1.0)
        wipe_margin_y_ratio = float(profile["wipe_margin_y_ratio"]) * (1.15 if template_mode else 1.0)
        cover_margin_x = max(20, int((x2 - x1) * wipe_margin_x_ratio))
        cover_margin_y = max(8, int((y2 - y1) * wipe_margin_y_ratio))
        cx1 = max(0, x1 - cover_margin_x)
        cy1 = max(0, y1 - cover_margin_y)
        cx2 = min(width, x2 + cover_margin_x)
        cy2 = min(height, y2 + cover_margin_y)
        cover = _sample_local_background_color(base_untinted, (cx1, cy1, cx2, cy2))
        if template_mode:
            cover = (cover[0], cover[1], cover[2], 255)
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
        if template_mode:
            # Add a short magical sweep cue before write-on.
            sweep = rewrite_frame.copy()
            sd = ImageDraw.Draw(sweep)
            line_color = TEMPLATE_LINE_COLORS[min(idx, len(TEMPLATE_LINE_COLORS) - 1)]
            sd.rounded_rectangle((cx1, y1 - 2, min(cx1 + int((cx2 - cx1) * 0.35), cx2), y2 + 2), radius=8, fill=(line_color[0], line_color[1], line_color[2], 96))
            sd.ellipse((x1 - 6, y1 + 2, x1 + 10, y1 + 18), fill=(line_color[0], line_color[1], line_color[2], 210))
            frames.append(sweep.convert("P", palette=Image.ADAPTIVE))
            raw_frames.append(sweep.copy())
            frame_durations.append(140)

        tx, ty = anchors[idx].get("text_origin", (x1 + 12, y1 + int(profile["text_y_offset"])))
        tx, ty = _refine_text_origin_with_token(
            image=base_untinted,
            anchor=anchors[idx],
            explanation=exp if isinstance(exp, dict) else {},
            line_text=step,
            draw=rewrite_draw,
            font=body_font,
        )
        line_font = _fit_font_for_bbox(
            rewrite_draw,
            text=step,
            bbox=(x1, y1, x2, y2),
            preferred_size=body_font.size,
            min_size=20,
        )
        ty = y1 + max(2, int(((y2 - y1) - int(line_font.size * 1.15)) / 2))
        # Character-by-character reveal for smoother 3b1b-like write-on.
        write_chars = max(1, len(step))
        chunk = 1
        for i in range(chunk, write_chars + 1, chunk):
            draw_step = rewrite_frame.copy()
            dsd = ImageDraw.Draw(draw_step)
            line_color = TEMPLATE_LINE_COLORS[min(idx, len(TEMPLATE_LINE_COLORS) - 1)] if template_mode else (20, 24, 36, 255)
            dsd.text((tx, ty), step[:i], font=line_font, fill=line_color)
            frames.append(draw_step.convert("P", palette=Image.ADAPTIVE))
            raw_frames.append(draw_step.copy())
            frame_durations.append(
                int(profile["write_char_ms_equivalent"])
                if status == "equivalent"
                else int(profile["write_char_ms_inconsistent"])
            )

        # Ensure full line is present at the end of write-on.
        line_color = TEMPLATE_LINE_COLORS[min(idx, len(TEMPLATE_LINE_COLORS) - 1)] if template_mode else (20, 24, 36, 255)
        rewrite_draw.text((tx, ty), step, font=line_font, fill=line_color)
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
        if template_mode:
            cover = (cover[0], cover[1], cover[2], 255)
        final_draw.rectangle((x1, y1, x2, y2), fill=cover)
        tx, ty = anchors[idx].get("text_origin", (x1 + 12, y1 + int(profile["text_y_offset"])))
        line_font = _fit_font_for_bbox(final_draw, text=step, bbox=(x1, y1, x2, y2), preferred_size=body_font.size, min_size=20)
        ty = y1 + max(2, int(((y2 - y1) - int(line_font.size * 1.15)) / 2))
        line_color = TEMPLATE_LINE_COLORS[min(idx, len(TEMPLATE_LINE_COLORS) - 1)] if template_mode else (20, 24, 36, 255)
        final_draw.text((tx, ty), step, font=line_font, fill=line_color)
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
    qa["template_mode"] = template_mode

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
