"""Synchronized wall-clock timing, without importing ML packages at startup."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from time import perf_counter_ns
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class TimedResult(Generic[T]):
    value: T
    elapsed_ms: float


def synchronize_device(device: object | None) -> None:
    """Wait for work on the selected CUDA device; CPU timing needs no torch."""
    if device is not None and str(device).split(":", 1)[0] == "cuda":
        torch = importlib.import_module("torch")
        torch.cuda.synchronize(device)


def timed_call(operation: Callable[[], T], *, device: object | None = None) -> TimedResult[T]:
    """Measure one operation including synchronization at its two boundaries.

    A full ``generate`` measurement is total generation latency. A later
    decoder measurement is reconstruction overhead, never generator lead time.
    Warmup, batch size, and hardware remain the experiment runner's concern.
    """
    synchronize_device(device)
    start = perf_counter_ns()
    value = operation()
    synchronize_device(device)
    return TimedResult(value, (perf_counter_ns() - start) / 1_000_000)
