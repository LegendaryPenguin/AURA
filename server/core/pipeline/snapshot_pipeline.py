from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage
from server.utils.logger import log_event


class PipelineTimeoutError(Exception):
    """Raised when the pipeline or a stage exceeds its timeout budget."""

    def __init__(self, message: str, status_code: int = 408) -> None:
        super().__init__(message)
        self.status_code = status_code


class SnapshotPipeline:
    """Chains pipeline stages in order with per-stage and total timeouts."""

    def __init__(
        self,
        stages: list[tuple[str, PipelineStage, float]],
        total_timeout_ms: float,
        include_timing: bool = False,
    ) -> None:
        """
        Args:
            stages: list of (stage_name, stage_instance, timeout_ms) tuples.
            total_timeout_ms: hard cap on end-to-end processing time.
            include_timing: if True, attach per-stage timing to the response.
        """
        self._stages = stages
        self._total_timeout_ms = total_timeout_ms
        self._include_timing = include_timing

    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:
        pipeline_start = time.monotonic()
        timing: list[dict[str, Any]] = []

        for stage_name, stage, timeout_ms in self._stages:
            elapsed_so_far_ms = (time.monotonic() - pipeline_start) * 1000
            if elapsed_so_far_ms >= self._total_timeout_ms:
                raise PipelineTimeoutError(
                    f"Pipeline total timeout ({self._total_timeout_ms}ms) exceeded "
                    f"before reaching stage '{stage_name}' "
                    f"(elapsed: {elapsed_so_far_ms:.0f}ms)"
                )

            remaining_ms = self._total_timeout_ms - elapsed_so_far_ms
            effective_timeout_s = min(timeout_ms, remaining_ms) / 1000

            stage_start = time.monotonic()
            try:
                context = self._execute_with_timeout(stage, context, effective_timeout_s)
            except FuturesTimeout:
                latency = (time.monotonic() - stage_start) * 1000
                log_event(stage_name, "timeout", latency, session_id)
                raise PipelineTimeoutError(
                    f"Stage '{stage_name}' timed out after {timeout_ms:.0f}ms"
                )
            except PipelineTimeoutError:
                raise
            except Exception as exc:
                latency = (time.monotonic() - stage_start) * 1000
                log_event(stage_name, "error", latency, session_id, error=str(exc))
                raise

            latency = (time.monotonic() - stage_start) * 1000
            log_event(stage_name, "ok", latency, session_id)
            timing.append({"stage": stage_name, "latency_ms": round(latency, 2)})

        total_ms = (time.monotonic() - pipeline_start) * 1000
        if self._include_timing and context.response is not None:
            context.response["_timing"] = {
                "stages": timing,
                "total_ms": round(total_ms, 2),
            }

        return context

    @staticmethod
    def _execute_with_timeout(
        stage: PipelineStage, context: PipelineContext, timeout_s: float
    ) -> PipelineContext:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(stage.execute, context)
            return future.result(timeout=timeout_s)
