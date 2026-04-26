from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIDEO_SIM_DIR = _REPO_ROOT / "video-simulation"
_VIDEO_SIM_OUTPUTS = _VIDEO_SIM_DIR / "outputs"
_CAPTURES_DIR = _VIDEO_SIM_OUTPUTS / "captures"
_MANUAL_STEPS_FILE = _VIDEO_SIM_OUTPUTS / "steps_to_edit.json"
_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _python_executable() -> str:
    if os.name == "nt":
        venv_py = _VIDEO_SIM_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = _VIDEO_SIM_DIR / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def _set_job(job_id: str, **fields: Any) -> None:
    with _JOBS_LOCK:
        state = _JOBS.setdefault(job_id, {})
        state.update(fields)


def _get_job(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        state = _JOBS.get(job_id)
        return dict(state) if state else None


def _run_video_sim_job(job_id: str, image_path: Path) -> None:
    _set_job(
        job_id,
        status="running",
        updated_at=_now_iso(),
        started_at=_now_iso(),
        message="rendering_video (typically 30-90s)",
    )
    _VIDEO_SIM_OUTPUTS.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    command = [
        _python_executable(),
        "pipeline/run_pipeline.py",
        "--image",
        str(image_path),
        "--pipeline-mode",
        "staged",
        "--manual-steps",
        str(_MANUAL_STEPS_FILE),
        "--style",
        "side_by_side_blueprint",
    ]
    try:
        env = dict(os.environ)
        env["AURA_VIDEO_SIM_FORCE_INPUT_IMAGE"] = "1"
        result = subprocess.run(
            command,
            cwd=str(_VIDEO_SIM_DIR),
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    except Exception as exc:  # pragma: no cover
        _set_job(
            job_id,
            status="error",
            updated_at=_now_iso(),
            message="generator_failed_to_start",
            error=str(exc),
        )
        logger.exception("video-sim job %s failed to start", job_id)
        return

    if result.returncode != 0:
        _set_job(
            job_id,
            status="error",
            updated_at=_now_iso(),
            message="generator_failed",
            error=(result.stderr or result.stdout or "unknown video simulation error")[:4000],
        )
        return

    rendered_path: Path | None = None
    for line in (result.stdout or "").splitlines():
        if line.startswith("Video file: "):
            candidate = Path(line.replace("Video file: ", "", 1).strip())
            if candidate.exists():
                rendered_path = candidate
                break

    if rendered_path is None:
        candidates = sorted(
            _VIDEO_SIM_OUTPUTS.glob("tutorial_animation_*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=UTC)
            if modified >= started_at:
                rendered_path = candidate
                break

    if rendered_path is None or not rendered_path.exists():
        _set_job(
            job_id,
            status="error",
            updated_at=_now_iso(),
            message="render_output_not_found",
            error="video render finished but output file could not be located",
        )
        return

    _set_job(
        job_id,
        status="done",
        updated_at=_now_iso(),
        completed_at=_now_iso(),
        message="video_ready",
        video_path=str(rendered_path),
    )


async def _extract_image_upload(request: Request) -> UploadFile:
    form = await request.form()
    for key in ("image", "image_file", "file"):
        candidate = form.get(key)
        if candidate is not None and hasattr(candidate, "read") and hasattr(candidate, "filename"):
            return candidate  # type: ignore[return-value]
    raise HTTPException(status_code=422, detail="multipart image file is required")


@router.post("/video-sim/capture")
async def capture_video_sim(request: Request) -> JSONResponse:
    upload = await _extract_image_upload(request)
    if not upload.filename:
        raise HTTPException(status_code=422, detail="uploaded image filename is required")
    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="uploaded file must be an image")

    suffix = Path(upload.filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    job_id = str(uuid4())
    _CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    capture_path = _CAPTURES_DIR / f"{job_id}{suffix}"
    image_bytes = await upload.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="uploaded image is empty")
    capture_path.write_bytes(image_bytes)

    created_at = _now_iso()
    _set_job(
        job_id,
        status="queued",
        created_at=created_at,
        updated_at=created_at,
        message="upload_received_queued",
        capture_path=str(capture_path),
    )
    worker = threading.Thread(target=_run_video_sim_job, args=(job_id, capture_path), daemon=True)
    worker.start()
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/video-sim/jobs/{job_id}",
            "video_url": f"/api/video-sim/video/{job_id}",
        },
    )


@router.get("/video-sim/jobs/{job_id}")
async def get_video_sim_job(job_id: str) -> JSONResponse:
    state = _get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found")
    payload: dict[str, Any] = {
        "job_id": job_id,
        "status": state.get("status", "unknown"),
        "message": state.get("message", ""),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "started_at": state.get("started_at"),
        "completed_at": state.get("completed_at"),
        "error": state.get("error"),
    }
    start_marker = state.get("started_at") or state.get("created_at")
    if isinstance(start_marker, str):
        try:
            start_dt = datetime.fromisoformat(start_marker)
            payload["elapsed_seconds"] = max(0, int((datetime.now(UTC) - start_dt).total_seconds()))
        except Exception:
            pass
    if state.get("status") == "done":
        payload["video_url"] = f"/api/video-sim/video/{job_id}"
    return JSONResponse(status_code=200, content=payload)


@router.get("/video-sim/video/{job_id}")
async def get_video_sim_video(job_id: str) -> FileResponse:
    state = _get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found")
    if state.get("status") != "done":
        raise HTTPException(status_code=409, detail="video is not ready")
    video_path = Path(str(state.get("video_path", "")))
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="video file not found")
    return FileResponse(path=str(video_path), media_type="video/mp4", filename=f"{job_id}.mp4")
