# Video Simulation (Image -> Tutor Video)

Local-only staged pipeline for handwritten algebra:

1. `vision_parse` (VLM-first local endpoint, OCR fallback)
2. `normalize` (canonical step text)
3. `verify` (SymPy symbolic checks, strict verified semantics)
4. `narrate` (pedagogical explanation + uncertainty labels)
5. `render` (Manim scene + optional video)

## Setup (Linux/macOS)

```bash
cd video-simulation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Setup (Windows PowerShell)

```powershell
cd video-simulation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

## One-command run (staged default)

```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --preview
```
`--style paper_clean` is the default and produces direct on-paper cover-and-rewrite correction.
Use `--style paper_3b1b` for a cleaner math-first motion/tint profile inspired by 3Blue1Brown pacing.

Staged mode is local-model-first and requires a local OpenAI-compatible VLM endpoint.
Set:

```bash
export VIDEO_SIM_VLM_ENDPOINT="http://127.0.0.1:8000/v1"
export VIDEO_SIM_VLM_MODEL_ID="Qwen/Qwen2.5-VL-7B-Instruct"
```

If needed, start local vLLM from repo root:

```bash
scripts/startup/start_vllm.sh
```

## Compatibility mode (rollback)

```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --pipeline-mode compat --preview
```

## Useful commands

- Stage-only dry run (no video render):
```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --skip-render
```

- Manual-steps fallback when VLM parse is unavailable:
```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --skip-render --manual-steps outputs/steps_to_edit.json
```

- Prepare editable steps:
```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --prepare-steps --skip-render
```

- Render using edited steps:
```bash
python pipeline/run_pipeline.py --image inputs/handwritten.png --use-edited-steps outputs/steps_to_edit.json --preview
```

## Output locations

- Final artifact: `outputs/ocr_result_<timestamp>.json`
- Generated scene: `outputs/generated_scene_<timestamp>.py`
- Per-stage artifacts: `outputs/stages/<timestamp>/*.json`
- Video output (preferred): MP4 (`media/videos/.../OCRMathScene.mp4` via Manim, or `outputs/tutorial_animation_<timestamp>.mp4` via Python fallback)
- GIF fallback only if MP4 render paths are unavailable.

`run_pipeline.py` prints the exact detected video path after rendering.

## Evaluation

```bash
python eval/evaluate_pipeline.py
python eval/ab_compare.py
```
