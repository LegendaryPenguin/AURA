from __future__ import annotations

from pathlib import Path


RIPPLE_SCENE_TEMPLATE = """from manimlib import *


class OCRMathScene(Scene):
    def construct(self):
        image_path = r\"\"\"{image_path}\"\"\"
        preview_mode = {preview_mode}
        display_steps = {display_steps}
        explanation_steps = {explanation_steps}
        final_check = {final_check}
        render_quality_grade = r\"\"\"{render_quality_grade}\"\"\"
        draft_mode = {draft_mode}

        title = Text("Algebra Tutor Walkthrough").scale(0.58).to_edge(UP)
        self.play(FadeIn(title, shift=UP), run_time=0.6)

        objective = Text("Goal: solve for x and verify", font_size=24).set_color(BLUE_B).next_to(title, DOWN, buff=0.15)
        quality_badge = Text(f"Draft quality: {{render_quality_grade}}", font_size=20).set_color(YELLOW).to_edge(UP, buff=0.2).shift(RIGHT * 4.5)
        self.play(FadeIn(objective), FadeIn(quality_badge), run_time=0.35)

        if image_path:
            source = ImageMobject(image_path).set_height(3.4).to_edge(LEFT, buff=0.45)
            source_frame = SurroundingRectangle(source, color=GREY_B, buff=0.08)
            self.play(FadeIn(source), ShowCreation(source_frame), run_time=0.6)

        panel = RoundedRectangle(width=7.2, height=5.8, corner_radius=0.12).set_color(GREY_B)
        panel.move_to(RIGHT * 2.95 + DOWN * 0.15)
        explanation_panel = RoundedRectangle(width=7.2, height=0.95, corner_radius=0.1).set_color(BLUE_E)
        explanation_panel.move_to(RIGHT * 2.95 + DOWN * 2.65)
        self.play(ShowCreation(panel), ShowCreation(explanation_panel), run_time=0.3)

        max_lines = max(len(display_steps), 1)
        line_gap = max(0.46, min(0.62, 3.2 / max_lines))
        right_x = 2.95
        top_y = 1.92

        step_mobs = VGroup()
        for i, step in enumerate(display_steps):
            line = Text(f"Step {{i+1}}: {{step}}", font_size=27).set_color(GREY_A)
            if line.get_width() > 6.1:
                line.set_width(6.1)
            line.move_to(RIGHT * right_x + UP * (top_y - i * line_gap))
            step_mobs.add(line)
        if step_mobs:
            self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.2) for m in step_mobs], lag_ratio=0.1), run_time=1.0)

        if draft_mode:
            draft = Text("Draft analysis (review suggested)", font_size=22).set_color(YELLOW).to_edge(DOWN, buff=0.45)
            self.play(FadeIn(draft), run_time=0.3)

        for exp in explanation_steps[:4]:
            line = Text(
                f"Step {{exp.get('from_index', 0)+1}}->{{exp.get('to_index', 0)+1}}: {{exp.get('operation', '')}} ({{exp.get('reason', '')}})",
                font_size=19,
            ).set_color(BLUE_B)
            if line.get_width() > 6.7:
                line.set_width(6.7)
            line.move_to(explanation_panel.get_center())
            self.play(FadeIn(line), run_time=0.35 if preview_mode else 0.55)
            self.wait(0.25 if preview_mode else 0.45)
            self.play(FadeOut(line), run_time=0.2 if preview_mode else 0.32)

        check_color = GREEN if final_check.get("status") == "pass" else RED
        check_msg = f"Final check: {{final_check.get('message', 'unknown')}} ({{final_check.get('lhs', '?')}} vs {{final_check.get('rhs', '?')}})"
        final_card = Text(check_msg, font_size=19).set_color(check_color)
        if final_card.get_width() > 6.8:
            final_card.set_width(6.8)
        final_card.move_to(explanation_panel.get_center())
        self.play(FadeIn(final_card), run_time=0.4)
        self.wait(0.8 if preview_mode else 1.2)
"""


def _escape(value: str) -> str:
    return value.replace('"""', r"\"\"\"")


def write_scene_file(
    output_path: Path,
    *,
    image_path: str,
    preview_mode: bool,
    story: dict,
) -> Path:
    content = RIPPLE_SCENE_TEMPLATE.format(
        image_path=_escape(image_path or ""),
        preview_mode=str(bool(preview_mode)),
        display_steps=repr(story.get("display_steps", [])),
        explanation_steps=repr(story.get("explanation_steps", [])),
        final_check=repr(story.get("final_check", {})),
        render_quality_grade=_escape(str(story.get("render_quality_grade", "low"))),
        draft_mode=str(bool(story.get("draft_mode", False))),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
