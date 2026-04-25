from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from build_scene import write_scene_file
from extract_math import build_tutor_story, extract_steps


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
    parser.add_argument("--allow-low-confidence", action="store_true", help="Accepted for compatibility; always-render mode in this package")
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
        steps_path.write_text(
            json.dumps(
                {
                    "input_image": str(image_path),
                    "editable_steps": steps,
                    "metadata": extraction_meta,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if args.prepare_steps:
            print(f"Steps file ready for manual edit: {steps_path}")
            return

    story = build_tutor_story(steps)
    scene_file = output_dir / f"generated_scene_{stamp}.py"
    write_scene_file(
        scene_file,
        image_path=str(image_path),
        preview_mode=args.preview,
        story=story,
    )

    artifact = {
        "timestamp": stamp,
        "input_image": str(image_path),
        "story_mode": args.story_mode,
        "story": story,
        "extraction": extraction_meta,
        "scene_file": str(scene_file),
        "render_quality_grade": story.get("render_quality_grade", "low"),
        "display_steps": story.get("display_steps", []),
        "hidden_noisy_steps": story.get("hidden_noisy_steps", []),
        "step_readability_scores": story.get("step_readability_scores", []),
    }
    json_path = output_dir / f"ocr_result_{stamp}.json"
    json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

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
    print("Render complete.")


if __name__ == "__main__":
    main()
