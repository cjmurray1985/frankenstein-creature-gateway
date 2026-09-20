from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator


_BOUNDARY = re.compile(r"(?<=[.!?;:])(?:\s+|$)")


class StableClauseBuffer:
    """Turns arbitrary text deltas into speakable, punctuation-stable clauses."""

    def __init__(self, minimum_characters: int = 12) -> None:
        if minimum_characters < 1:
            raise ValueError("minimum_characters must be positive")
        self.minimum_characters = minimum_characters
        self._buffer = ""

    def push(self, delta: str) -> list[str]:
        self._buffer += delta
        ready: list[str] = []
        while True:
            match = next(
                (
                    boundary
                    for boundary in _BOUNDARY.finditer(self._buffer)
                    if len(self._buffer[: boundary.end()].strip()) >= self.minimum_characters
                ),
                None,
            )
            if match is None:
                break
            candidate = self._buffer[: match.end()].strip()
            ready.append(candidate)
            self._buffer = self._buffer[match.end() :]
        return ready

    def flush(self) -> str | None:
        remainder = self._buffer.strip()
        self._buffer = ""
        return remainder or None


def stable_clauses(deltas: Iterable[str], minimum_characters: int = 12) -> Iterator[str]:
    buffer = StableClauseBuffer(minimum_characters)
    for delta in deltas:
        yield from buffer.push(delta)
    remainder = buffer.flush()
    if remainder is not None:
        yield remainder


@dataclass(frozen=True)
class IncrementalTiming:
    started_at: float
    first_text_at: float | None
    first_clause_at: float | None
    completed_at: float

    @property
    def first_text_seconds(self) -> float | None:
        return None if self.first_text_at is None else self.first_text_at - self.started_at

    @property
    def first_clause_seconds(self) -> float | None:
        return None if self.first_clause_at is None else self.first_clause_at - self.started_at

    @property
    def total_seconds(self) -> float:
        return self.completed_at - self.started_at


def observe_stable_clauses(
    deltas: Iterable[str],
    on_clause: Callable[[str], None],
    *,
    minimum_characters: int = 12,
    clock: Callable[[], float] = time.monotonic,
) -> IncrementalTiming:
    """Measure when streamed text first becomes safe to hand to TTS."""

    started = clock()
    first_text_at: float | None = None
    first_clause_at: float | None = None
    buffer = StableClauseBuffer(minimum_characters)
    for delta in deltas:
        if delta and first_text_at is None:
            first_text_at = clock()
        for clause in buffer.push(delta):
            if first_clause_at is None:
                first_clause_at = clock()
            on_clause(clause)
    remainder = buffer.flush()
    if remainder is not None:
        if first_clause_at is None:
            first_clause_at = clock()
        on_clause(remainder)
    return IncrementalTiming(started, first_text_at, first_clause_at, clock())
