# WS4-A: VLM Backend

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `In-Progress`                    |
| **Owner**   | `Farrell`                        |
| **Phase**   | Phase 1                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/inference/vlm/__init__.py`
- `server/core/inference/vlm/qwen_vl.py`
- `server/core/inference/vlm/llava.py`
- `tests/unit/inference/test_vlm_backends.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `qwen_vl.py`: implement `InferenceBackend` for Qwen2.5-VL-7B via vLLM OpenAI-compatible API. `analyze(image_b64, query) → OverlayResponse`. System prompt enforces JSON-only output with normalized coordinates.
- `llava.py`: implement `InferenceBackend` for LLaVA as fallback (smaller, faster, less accurate).
- Prompt engineering: design system prompt requiring JSON-only output, no markdown, normalized coords. Test against 20 images. Target: 80%+ bounding boxes land correctly. Iterate prompt until this bar is met.

---

## Verification

- [ ] `load()` → `warmup()` → `is_ready()` returns True (with vLLM running)
- [ ] `analyze()` with test fixture image returns valid JSON matching schema
- [ ] Bounding box coordinates are within [0,1] range
- [ ] 80%+ of bounding boxes land on correct object region across 20 test images
- [ ] Response time under 2 seconds for 7B model
- [ ] `llava.py` passes same interface tests (lower accuracy acceptable)
- [ ] Unit test: VLM output passes schema validation for all fixture images
