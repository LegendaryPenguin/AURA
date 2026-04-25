from __future__ import annotations

import os

from .qwen_vl import OpenAIVLMBackend


class LlavaVLMBackend(OpenAIVLMBackend):
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model_id: str | None = None,
        timeout_ms: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        super().__init__(
            model_id=model_id or os.getenv("AURA_VLM_LLAVA_MODEL_ID", "llava-hf/llava-1.5-7b-hf"),
            endpoint=endpoint,
            timeout_ms=timeout_ms,
            max_tokens=max_tokens or int(os.getenv("AURA_VLM_MAX_TOKENS", "160")),
        )
