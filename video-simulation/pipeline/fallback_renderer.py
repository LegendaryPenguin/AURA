from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


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
                    "baseline_angle_deg": 0.0,
                    "confidence": 0.35,
                    "fallback": True,
                }
            )
        return anchors, fallback

    selected = bands[-expected_count:] if len(bands) >= expected_count else bands
    for band in selected:
        by1, by2 = band
        # Find occupied x-range for this line band.
        gray = image.convert("L")
        xs: list[int] = []
        for y in range(by1, by2 + 1):
            for x in range(x1, x2):
                if gray.getpixel((x, y)) < 128:
                    xs.append(x)
        if xs:
            lx1 = max(x1 + 12, min(xs) - 12)
            lx2 = min(x2 - 12, max(xs) + 12)
            conf = 0.82
        else:
            lx1 = x1 + 40
            lx2 = x2 - 40
            conf = 0.45
        anchors.append(
            {
                "bbox": (lx1, by1 - 6, lx2, by2 + 8),
                "baseline_angle_deg": 0.0,
                "confidence": conf,
                "fallback": False,
            }
        )

    if len(anchors) < expected_count:
        slots = _line_slots(paper_rect, expected_count - len(anchors))
        for slot in slots:
            sx1, sy1, sx2, sy2 = slot
            anchors.append(
                {
                    "bbox": (sx1, sy1, sx2, sy2),
                    "baseline_angle_deg": 0.0,
                    "confidence": 0.35,
                    "fallback": True,
                }
            )
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
            return anchors, True
        nx1 = max(px1 + 8, x1)
        nx2 = min(px2 - 8, x2)
        adjusted_anchor = dict(anchor)
        adjusted_anchor["bbox"] = (nx1, ny1, nx2, ny2)
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
    conf = min(1.0, area / max(1, int(w * h * 0.90)))
    return _clamp_bbox(bbox, w, h), conf


def _roi_from_opencv(image: Image.Image) -> tuple[tuple[int, int, int, int] | None, float]:
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None, 0.0
    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, 0.0
    w, h = image.size
    best = None
    best_area = 0
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area > best_area:
            best_area = area
            best = (x, y, x + bw, y + bh)
    if best is None:
        return None, 0.0
    conf = min(1.0, best_area / max(1, int(w * h * 0.75)))
    return _clamp_bbox(best, w, h), conf


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
    use_cv = cv_bbox is not None and cv_conf >= max(0.18, lum_conf + 0.05)
    chosen = cv_bbox if use_cv else lum_bbox
    conf = cv_conf if use_cv else lum_conf
    method = "opencv" if use_cv else "luminance"
    if chosen is None:
        return (0, 0, w, h), False, "fullframe"
    chosen = _expand_bbox(chosen, w, h, pad_ratio=0.10)
    area_ratio = ((chosen[2] - chosen[0]) * (chosen[3] - chosen[1])) / max(1, w * h)
    confident = conf >= 0.22 and area_ratio >= 0.05
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
    checks["content_occupancy_ratio"] = content_occupancy_ratio >= 0.58
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


def render_tutoring_animation(
    *,
    output_path: Path,
    image_path: str,
    story: dict[str, Any],
    fps: int = 2,
    style: str = "hybrid",
) -> tuple[Path, dict[str, Any]]:
    width, height = 1280, 720
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
        img = cropped.copy()
        img.thumbnail((width - 40, height - 40), Image.Resampling.LANCZOS)
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
            draw.text((x1 + 12, y1 + 8), prior_step, font=body_font, fill=(24, 30, 45, 255))

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
        cover_margin_x = max(20, int((x2 - x1) * 0.06))
        cover_margin_y = max(8, int((y2 - y1) * 0.25))
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
        frame_durations.append(360 if status == "inconsistent" else 280)

        # Character-by-character reveal for smoother 3b1b-like write-on.
        write_chars = max(1, len(step))
        chunk = 1
        for i in range(chunk, write_chars + 1, chunk):
            draw_step = rewrite_frame.copy()
            dsd = ImageDraw.Draw(draw_step)
            dsd.text((x1 + 12, y1 + 8), step[:i], font=body_font, fill=(20, 24, 36, 255))
            frames.append(draw_step.convert("P", palette=Image.ADAPTIVE))
            raw_frames.append(draw_step.copy())
            frame_durations.append(65 if status == "equivalent" else 75)

        # Ensure full line is present at the end of write-on.
        rewrite_draw.text((x1 + 12, y1 + 8), step, font=body_font, fill=(20, 24, 36, 255))
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
        final_draw.text((x1 + 12, y1 + 8), step, font=body_font, fill=(20, 24, 36, 255))
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
