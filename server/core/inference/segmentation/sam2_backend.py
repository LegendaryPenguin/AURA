from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SAM2Backend:
    """SAM2 segmentation backend for generating masks from bounding boxes.

    Accepts JPEG image bytes + a normalized [x, y, w, h] bounding box, and
    returns an RLE-encoded binary mask. Falls back gracefully if the SAM2
    library or checkpoint is unavailable.
    """

    def __init__(
        self,
        checkpoint_path: str = "models/sam2/sam2_large.pt",
        device: str = "auto",
    ) -> None:
        self._checkpoint_path = checkpoint_path
        self._device = device
        self._model: Any = None
        self._ready = False

    def load(self) -> None:
        try:
            self._try_load_sam2()
            self._ready = True
        except ImportError:
            logger.warning(
                "SAM2 / segment-anything-2 not installed; segmentation disabled. "
                "Falling back to bbox-only masks."
            )
            self._ready = False
        except FileNotFoundError:
            logger.warning(
                "SAM2 checkpoint not found at %s; using bbox-only fallback",
                self._checkpoint_path,
            )
            self._ready = False
        except Exception as exc:
            logger.warning("SAM2 load failed: %s; using bbox-only fallback", exc)
            self._ready = False

    def _try_load_sam2(self) -> None:
        from sam2.build_sam import build_sam2  # type: ignore[import-untyped]
        from sam2.sam2_image_predictor import SAM2ImagePredictor  # type: ignore[import-untyped]
        import torch

        device = self._device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        sam2_model = build_sam2("sam2_l", self._checkpoint_path, device=device)
        self._model = SAM2ImagePredictor(sam2_model)
        logger.info("SAM2 loaded from %s on %s", self._checkpoint_path, device)

    def is_ready(self) -> bool:
        return self._ready

    def segment(self, image_bytes: bytes, bbox: list[float]) -> dict[str, Any]:
        """Generate a segmentation mask from image + normalized bbox.

        Returns dict with 'mask_rle' (run-length encoded mask), 'bbox', and
        'score'. If SAM2 is unavailable, returns a synthetic rectangular mask
        derived from the bounding box.
        """
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size

        abs_bbox = [
            bbox[0] * w,
            bbox[1] * h,
            (bbox[0] + bbox[2]) * w,
            (bbox[1] + bbox[3]) * h,
        ]

        if self._ready and self._model is not None:
            return self._segment_with_sam2(img, abs_bbox)

        return self._bbox_fallback_mask(w, h, abs_bbox, bbox)

    def _segment_with_sam2(
        self, img: Any, abs_bbox: list[float]
    ) -> dict[str, Any]:
        import torch

        img_array = np.array(img)
        self._model.set_image(img_array)

        box_tensor = torch.tensor([abs_bbox], dtype=torch.float32)
        masks, scores, _ = self._model.predict(
            box=box_tensor.numpy(),
            multimask_output=False,
        )

        mask = masks[0].astype(bool)
        rle = self._mask_to_rle(mask)

        return {
            "mask_rle": rle,
            "bbox": abs_bbox,
            "score": float(scores[0]),
            "width": img.size[0],
            "height": img.size[1],
        }

    def _bbox_fallback_mask(
        self,
        img_w: int,
        img_h: int,
        abs_bbox: list[float],
        norm_bbox: list[float],
    ) -> dict[str, Any]:
        """Synthetic rectangular mask when SAM2 is not available."""
        mask = np.zeros((img_h, img_w), dtype=bool)
        x1 = max(0, int(abs_bbox[0]))
        y1 = max(0, int(abs_bbox[1]))
        x2 = min(img_w, int(abs_bbox[2]))
        y2 = min(img_h, int(abs_bbox[3]))
        mask[y1:y2, x1:x2] = True

        rle = self._mask_to_rle(mask)
        return {
            "mask_rle": rle,
            "bbox": abs_bbox,
            "score": 0.85,
            "width": img_w,
            "height": img_h,
        }

    @staticmethod
    def _mask_to_rle(mask: np.ndarray) -> dict[str, Any]:
        """Convert binary mask to COCO-style run-length encoding."""
        flat = mask.flatten(order="F")
        diff = np.diff(np.concatenate([[0], flat, [0]]))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        lengths = ends - starts

        counts: list[int] = []
        pos = 0
        for s, length in zip(starts, lengths):
            counts.append(int(s - pos))
            counts.append(int(length))
            pos = s + length
        if pos < len(flat):
            counts.append(int(len(flat) - pos))

        return {
            "counts": counts,
            "size": [int(mask.shape[0]), int(mask.shape[1])],
        }
