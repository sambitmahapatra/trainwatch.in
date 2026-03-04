"""Runtime tracking utilities."""

from dataclasses import dataclass
import time
from typing import Optional


@dataclass
class RuntimeTracker:
    _start: Optional[float] = None
    _end: Optional[float] = None

    def start(self) -> None:
        self._start = time.perf_counter()
        self._end = None

    def stop(self) -> float:
        if self._start is None:
            return 0.0
        self._end = time.perf_counter()
        return self.elapsed_seconds

    @property
    def elapsed_seconds(self) -> float:
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.perf_counter()
        return max(0.0, end - self._start)

    def reset(self) -> None:
        self._start = None
        self._end = None
