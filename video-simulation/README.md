# Video Simulation (Image -> Tutorial Video)

This folder is a self-contained mini-project that:

1. reads an image of handwritten algebra,
2. extracts line-by-line steps with local OCR,
3. derives a tutoring story (mistake/ripple/correction),
4. generates a Manim scene and renders a video.

It is isolated from the rest of the AURA repo.

## Folder layout

- `pipeline/extract_math.py` - OCR, normalization, algebra parsing/story derivation
- `pipeline/build_scene.py` - scene template generator
- `pipeline/run_pipeline.py` - end-to-end runner (OCR -> scene -> render)
- `requirements.txt` - Python dependencies

## Prerequisites

- Python 3.10+
- Tesseract OCR installed and on PATH (Windows default path is auto-detected)
- FFmpeg on PATH
- ManimGL available (`manimgl` command) or in `.venv/Scripts/manimgl.exe`

## Setup

```powershell
cd video-simulation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe .\pipeline\run_pipeline.py --image .\inputs\handwritten.png --story-mode ripple --preview
```

## Useful modes

- Prepare editable OCR steps:
```powershell
.\.venv\Scripts\python.exe .\pipeline\run_pipeline.py --image .\inputs\handwritten.png --story-mode ripple --prepare-steps
```

- Render from edited steps:
```powershell
.\.venv\Scripts\python.exe .\pipeline\run_pipeline.py --image .\inputs\handwritten.png --story-mode ripple --use-edited-steps .\outputs\steps_to_edit.json --preview
```

- Force draft preview when confidence is low:
```powershell
.\.venv\Scripts\python.exe .\pipeline\run_pipeline.py --image .\inputs\handwritten.png --story-mode ripple --allow-low-confidence --preview
```

## Output

- Artifacts: `outputs/ocr_result_<timestamp>.json`, `outputs/generated_scene_<timestamp>.py`
- Video: written by ManimGL in its media output path (typically under `manim/videos/` or local media folder depending on ManimGL config)
