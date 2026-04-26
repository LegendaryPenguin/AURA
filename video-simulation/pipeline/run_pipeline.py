from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from build_scene import write_scene_file
from fallback_renderer import render_tutoring_animation
from narrate import run_stage as narrate_stage
from normalize import run_stage as normalize_stage
from verify import run_stage as verify_stage
from vision_parse import run_stage as vision_parse_stage

try:
    import jsonschema
except Exception:
    jsonschema = None


def _run_command(command: list[str], cwd: Path, extra_path_entries: list[str] | None = None) -> None:
    env = dict(**subprocess.os.environ)
    if extra_path_entries:
        env["PATH"] = subprocess.os.pathsep.join(extra_path_entries + [env.get("PATH", "")])
    result = subprocess.run(command, cwd=str(cwd), check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def _detect_tesseract() -> str | None:
    which = shutil.which("tesseract")
    if which:
        return which
    fallback = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    return str(fallback) if fallback.exists() else None


def _detect_ffmpeg_bin_dir() -> str | None:
    which = shutil.which("ffmpeg")
    return str(Path(which).parent) if which else None


def _detect_manimgl_executable(venv_path: Path) -> list[str]:
    exe = venv_path / "Scripts" / "manimgl.exe"
    py = venv_path / "Scripts" / "python.exe"
    if exe.exists():
        return [str(exe)]
    if py.exists():
        return [str(py), "-m", "manimlib"]
    return ["manimgl"]


def _validate_schema(schema_path: Path, payload: dict) -> None:
    if jsonschema is None:
        raise RuntimeError(
            "jsonschema package is required for staged pipeline. "
            "Install dependencies from video-simulation/requirements.txt."
        )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _detect_video_output(root_dir: Path) -> str | None:
    videos_dir = root_dir / "media" / "videos"
    if not videos_dir.exists():
        return None
    mp4s = sorted(videos_dir.rglob("OCRMathScene*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(mp4s[0]) if mp4s else None


def _can_render_manim(venv_dir: Path) -> bool:
    ffmpeg_ok = _detect_ffmpeg_bin_dir() is not None
    exe = venv_dir / "Scripts" / "manimgl.exe"
    py = venv_dir / "Scripts" / "python.exe"
    manim_cmd_ok = exe.exists() or py.exists() or shutil.which("manimgl") is not None
    return ffmpeg_ok and manim_cmd_ok


def _run_compat_mode(
    args: argparse.Namespace,
    image_path: Path,
    output_dir: Path,
    script_dir: Path,
    root_dir: Path,
    venv_dir: Path,
    stamp: str,
) -> None:
    from extract_math import build_tutor_story, extract_steps

    steps: list[str] = []
    extraction_meta: dict = {}
    if args.use_edited_steps:
        payload = json.loads(Path(args.use_edited_steps).read_text(encoding="utf-8"))
        steps = [str(s).strip() for s in payload.get("editable_steps", []) if str(s).strip()]
    else:
        tesseract_cmd = _detect_tesseract()
        extracted = extract_steps(image_path=image_path, tesseract_cmd=tesseract_cmd)
        steps = extracted.steps
        extraction_meta = {
            "avg_confidence": extracted.avg_conf,
            "confidences": extracted.confidences,
            "notes": extracted.notes,
        }
        steps_path = output_dir / "steps_to_edit.json"
        _write_json(
            steps_path,
            {
                "input_image": str(image_path),
                "editable_steps": steps,
                "metadata": extraction_meta,
            },
        )
        if args.prepare_steps:
            print(f"Steps file ready for manual edit: {steps_path}")
            return

    story = build_tutor_story(steps)
    scene_file = output_dir / f"generated_scene_{stamp}.py"
    write_scene_file(scene_file, image_path=str(image_path), preview_mode=args.preview, story=story)

    artifact = {
        "timestamp": stamp,
        "pipeline_mode": "compat",
        "input_image": str(image_path),
        "story_mode": args.story_mode,
        "story": story,
        "extraction": extraction_meta,
        "scene_file": str(scene_file),
    }
    json_path = output_dir / f"ocr_result_{stamp}.json"
    _write_json(json_path, artifact)

    if args.skip_render:
        print(f"Scene file: {scene_file}")
        print(f"OCR artifact: {json_path}")
        print("Skipped render (--skip-render).")
        return

    ffmpeg_bin_dir = _detect_ffmpeg_bin_dir()
    if not ffmpeg_bin_dir:
        raise RuntimeError("FFmpeg not found. Install FFmpeg or run with --skip-render.")
    manim_cmd = _detect_manimgl_executable(venv_dir)
    render_cmd = [*manim_cmd, str(scene_file), "OCRMathScene", "-w", f"-q{args.quality}"]
    _run_command(render_cmd, cwd=root_dir, extra_path_entries=[ffmpeg_bin_dir])
    print(f"Scene file: {scene_file}")
    print(f"OCR artifact: {json_path}")
    print(f"Video file: {_detect_video_output(root_dir) or 'not_found'}")
    print("Render complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Image -> tutorial video pipeline")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output-dir", default="../outputs", help="Output artifact directory")
    parser.add_argument("--quality", default="l", choices=["l", "m", "h", "k"], help="Manim quality preset")
    parser.add_argument("--preview", action="store_true", help="Use faster animation timing")
    parser.add_argument("--skip-render", action="store_true", help="Do not render video, only produce scene/artifact")
    parser.add_argument("--story-mode", default="ripple", choices=["ripple"], help="Tutor mode")
    parser.add_argument("--prepare-steps", action="store_true", help="Write steps_to_edit.json and exit")
    parser.add_argument("--use-edited-steps", default="", help="Use edited steps JSON file")
    parser.add_argument("--manual-steps", default="", help="Manual steps JSON fallback for staged mode when VLM parse fails")
    parser.add_argument(
        "--style",
        default="paper_clean",
        choices=["paper_clean", "hybrid", "minimal", "paper_3b1b", "side_by_side_blueprint"],
        help="Rendering style profile",
    )
    parser.add_argument("--allow-low-confidence", action="store_true", help="Accepted for compatibility; always-render mode in this package")
    parser.add_argument("--pipeline-mode", default="staged", choices=["staged", "compat"], help="Run staged JSON pipeline or legacy compatibility path")
    parser.add_argument("--compat-mode", action="store_true", help="Alias for --pipeline-mode compat")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent
    venv_dir = root_dir / ".venv"
    image_path = Path(args.image).expanduser().resolve()
    output_dir = (script_dir / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    use_compat = args.compat_mode or args.pipeline_mode == "compat"
    if use_compat:
        _run_compat_mode(args, image_path, output_dir, script_dir, root_dir, venv_dir, stamp)
        return

    schemas_dir = root_dir / "schemas"
    stage_dir = output_dir / "stages" / stamp
    stage_dir.mkdir(parents=True, exist_ok=True)
    vision = vision_parse_stage(image_path=image_path)
    _validate_schema(schemas_dir / "vision_parse.schema.json", vision)
    _write_json(stage_dir / "vision_parse.json", vision)

    manual_steps_file = args.use_edited_steps or args.manual_steps
    if vision.get("parse_status") != "ok" and not manual_steps_file:
        if args.prepare_steps:
            template_steps = [
                "6x+20+4(2x)=48",
                "6x+20+10x=48",
                "16x+20=48",
                "16x=28",
                "x=28/16",
            ]
            template_path = output_dir / "steps_to_edit.json"
            _write_json(
                template_path,
                {
                    "input_image": str(image_path),
                    "editable_steps": template_steps,
                    "metadata": {
                        "source": "manual_template",
                        "notes": vision.get("notes", []),
                    },
                },
            )
            print(f"Manual steps template ready: {template_path}")
            return
        notes = "; ".join(str(n) for n in vision.get("notes", [])) or "unknown"
        raise RuntimeError(
            "Local VLM parsing failed in staged mode. "
            "Provide manual steps with --manual-steps <json> or --use-edited-steps <json>. "
            f"Parser notes: {notes}"
        )

    if manual_steps_file and vision.get("parse_status") != "ok":
        edited_payload = json.loads(Path(manual_steps_file).read_text(encoding="utf-8"))
        manual_steps = [str(s).strip() for s in edited_payload.get("editable_steps", []) if str(s).strip()]
        if not manual_steps:
            raise RuntimeError("Manual steps file does not contain non-empty editable_steps")
        vision["notes"] = vision.get("notes", []) + ["manual_steps_fallback_applied"]
        vision["lines"] = [{"text": s, "confidence": 1.0, "source": "manual"} for s in manual_steps]
        vision["parse_status"] = "ok"
        vision["parser"] = "manual-steps"
        _write_json(stage_dir / "vision_parse_manual_fallback.json", vision)

    normalized = normalize_stage(vision)
    _validate_schema(schemas_dir / "normalize.schema.json", normalized)
    _write_json(stage_dir / "normalize.json", normalized)
    if args.prepare_steps:
        _write_json(output_dir / "steps_to_edit.json", {"input_image": str(image_path), "editable_steps": normalized["normalized_steps"]})
        print(f"Steps file ready for manual edit: {output_dir / 'steps_to_edit.json'}")
        return

    if args.use_edited_steps:
        edited_payload = json.loads(Path(args.use_edited_steps).read_text(encoding="utf-8"))
        normalized["normalized_steps"] = [
            str(s).strip() for s in edited_payload.get("editable_steps", []) if str(s).strip()
        ]
        _write_json(stage_dir / "normalize_edited.json", normalized)

    verified = verify_stage(normalized)
    _validate_schema(schemas_dir / "verify.schema.json", verified)
    _write_json(stage_dir / "verify.json", verified)

    narrated = narrate_stage(normalized, verified)
    _validate_schema(schemas_dir / "narrate.schema.json", narrated)
    _write_json(stage_dir / "narrate.json", narrated)

    story = {
        "display_steps": narrated["display_steps"],
        "corrected_steps": narrated.get("corrected_steps", narrated["display_steps"]),
        "explanation_steps": narrated["explanation_steps"],
        "final_check": verified["final_check"],
        "render_quality_grade": narrated["render_quality_grade"],
        "draft_mode": narrated["draft_mode"],
        "narration_intro": narrated["narration_intro"],
        "narration_outro": narrated["narration_outro"],
        "visual_style": args.style,
        "phase_labels": narrated.get("phase_labels", []),
    }
    scene_file = output_dir / f"generated_scene_{stamp}.py"
    write_scene_file(scene_file, image_path=str(image_path), preview_mode=args.preview, story=story)

    render_stage = {
        "stage": "render",
        "scene_file": str(scene_file),
        "render_quality_grade": narrated["render_quality_grade"],
        "draft_mode": narrated["draft_mode"],
    }
    _validate_schema(schemas_dir / "render.schema.json", render_stage)
    _write_json(stage_dir / "render.json", render_stage)

    artifact = {
        "timestamp": stamp,
        "pipeline_mode": "staged",
        "input_image": str(image_path),
        "story_mode": args.story_mode,
        "vision_parse": vision,
        "normalize": normalized,
        "verify": verified,
        "narrate": narrated,
        "render": render_stage,
    }
    json_path = output_dir / f"ocr_result_{stamp}.json"
    _write_json(json_path, artifact)

    if args.skip_render:
        print(f"Scene file: {scene_file}")
        print(f"OCR artifact: {json_path}")
        print(f"Stage artifacts: {stage_dir}")
        print("Skipped render (--skip-render).")
        return

    if _can_render_manim(venv_dir):
        ffmpeg_bin_dir = _detect_ffmpeg_bin_dir()
        manim_cmd = _detect_manimgl_executable(venv_dir)
        render_cmd = [*manim_cmd, str(scene_file), "OCRMathScene", "-w", f"-q{args.quality}"]
        _run_command(render_cmd, cwd=root_dir, extra_path_entries=[ffmpeg_bin_dir] if ffmpeg_bin_dir else None)
        video_output = _detect_video_output(root_dir) or "not_found"
    else:
        fallback_video = output_dir / f"tutorial_animation_{stamp}.mp4"
        rendered_video, qa_report = render_tutoring_animation(
            output_path=fallback_video,
            image_path=str(image_path),
            story=story,
            fps=2 if args.preview else 1,
            style=args.style,
        )
        video_output = str(rendered_video)
        render_stage["qa_report"] = qa_report
        _write_json(stage_dir / "render.json", render_stage)
        if str(rendered_video).endswith(".mp4"):
            print("Manim unavailable; rendered fallback animation (timed MP4 path).")
        else:
            print("Manim/MP4 unavailable; rendered GIF fallback animation.")
    print(f"Scene file: {scene_file}")
    print(f"OCR artifact: {json_path}")
    print(f"Stage artifacts: {stage_dir}")
    print(f"Video file: {video_output}")
    print("Render complete.")


if __name__ == "__main__":
    main()
