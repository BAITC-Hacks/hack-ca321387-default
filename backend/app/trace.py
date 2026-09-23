"""Opt-in monotonic measurements and sanitized notices from the actual execution."""
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter_ns

from .feature_schemas import StageTiming, TraceNotice


@dataclass
class TraceRecorder:
    stages: list[StageTiming] = field(default_factory=list)
    notices: list[TraceNotice] = field(default_factory=list)

    def record(self, stage: str, elapsed_ms: float, before: int | None = None, after: int | None = None) -> None:
        self.stages.append(StageTiming(stage=stage, elapsed_ms=elapsed_ms, before=before, after=after))


@contextmanager
def measured(recorder: TraceRecorder | None, stage: str) -> Iterator[None]:
    if recorder is None:
        yield
        return
    start = perf_counter_ns()
    try:
        yield
    finally:
        recorder.record(stage, (perf_counter_ns() - start) / 1_000_000)
