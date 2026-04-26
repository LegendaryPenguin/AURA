from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fallback_renderer import (
    _anchors_overlap_risk,
    _detect_content_roi,
    _detect_line_anchors,
    _refine_text_origin_with_token,
    _stabilize_anchors,
    render_tutoring_animation,
)


def _synthetic_equation_image(width: int = 900, height: int = 520) -> Image.Image:
    image = Image.new("RGB", (width, height), (244, 244, 236))
    draw = ImageDraw.Draw(image)
    lines = [
        "6x+20+4(2x)=48",
        "6x+20+8x=48",
        "14x+20=48",
        "14x=28",
        "x=2",
    ]
    y = 95
    for text in lines:
        draw.text((120, y), text, fill=(16, 16, 16))
        y += 68
    return image


def test_roi_detection_is_deterministic_on_static_input() -> None:
    image = _synthetic_equation_image()
    roi_a = _detect_content_roi(image)
    roi_b = _detect_content_roi(image)
    assert roi_a == roi_b


def test_anchor_detection_is_ordered_and_non_overlapping() -> None:
    image = _synthetic_equation_image()
    paper_rect, _, _ = _detect_content_roi(image)
    anchors, _ = _detect_line_anchors(image, paper_rect, expected_count=5)
    anchors, _ = _stabilize_anchors(anchors, paper_rect)
    assert len(anchors) == 5
    ys = [a["bbox"][1] for a in anchors]
    assert ys == sorted(ys)
    assert _anchors_overlap_risk(anchors) is False


def test_token_refinement_moves_origin_toward_visible_ink() -> None:
    image = _synthetic_equation_image()
    paper_rect, _, _ = _detect_content_roi(image)
    anchors, _ = _detect_line_anchors(image, paper_rect, expected_count=5)
    anchor = anchors[0]
    draw = ImageDraw.Draw(image)
    base_x, base_y = anchor.get("text_origin", (anchor["bbox"][0] + 12, anchor["bbox"][1] + 8))
    refined_x, refined_y = _refine_text_origin_with_token(
        image=image,
        anchor=anchor,
        explanation={"token_diff": {"from_tokens": ["6x"], "to_tokens": ["8x"]}},
        line_text="6x+20+4(2x)=48",
        draw=draw,
        font=ImageFont.load_default(),
    )
    assert refined_y == base_y
    assert abs(refined_x - base_x) <= 80


def test_render_alignment_is_stable_across_two_runs(tmp_path: Path) -> None:
    input_image = tmp_path / "equation.png"
    _synthetic_equation_image().save(input_image)
    story = {
        "display_steps": [
            "6x + 20 + 4(2x) = 48",
            "6x + 20 + 8x = 48",
            "14x + 20 = 48",
            "14x = 28",
            "x = 2",
        ],
        "explanation_steps": [{"validation": "equivalent"} for _ in range(5)],
        "final_check": {"status": "pass"},
    }

    out_a = tmp_path / "a.gif"
    out_b = tmp_path / "b.gif"
    _, qa_a = render_tutoring_animation(
        output_path=out_a,
        image_path=str(input_image),
        story=story,
        fps=2,
        style="paper_3b1b",
    )
    _, qa_b = render_tutoring_animation(
        output_path=out_b,
        image_path=str(input_image),
        story=story,
        fps=2,
        style="paper_3b1b",
    )
    checks_a = qa_a.get("checks", {})
    checks_b = qa_b.get("checks", {})
    assert checks_a.get("anchor_count_matches_steps") is True
    assert checks_a.get("anchors_inside_frame") is True
    assert checks_a.get("anchors_vertically_ordered") is True
    assert checks_b.get("anchor_count_matches_steps") is True
    assert checks_b.get("anchors_inside_frame") is True
    assert checks_b.get("anchors_vertically_ordered") is True
    bbox_a = qa_a.get("transform_meta", {}).get("source_bbox")
    bbox_b = qa_b.get("transform_meta", {}).get("source_bbox")
    assert bbox_a == bbox_b
