"""Playback-reference primitives for future echo-aware full duplex audio."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .audio import pcm_rms


@dataclass(frozen=True)
class ReferenceFrame:
    at_ms: int
    rms: int


@dataclass
class PlaybackReferenceRing:
    """Bounded outgoing-audio history; contains no microphone or GPIO access."""

    retention_ms: int = 2500
    frames: deque[ReferenceFrame] = field(default_factory=deque)

    def record_pcm(self, chunk: bytes, *, at_ms: int, sample_width: int = 2, channels: int = 1) -> None:
        self.frames.append(ReferenceFrame(at_ms, pcm_rms(chunk, sample_width, channels)))
        cutoff = at_ms - self.retention_ms
        while self.frames and self.frames[0].at_ms < cutoff:
            self.frames.popleft()

    def nearest_rms(self, at_ms: int, *, delay_ms: int = 0) -> int:
        target = at_ms - delay_ms
        if not self.frames:
            return 0
        return min(self.frames, key=lambda frame: abs(frame.at_ms - target)).rms


@dataclass(frozen=True)
class ResidualEstimate:
    captured_rms: int
    reference_rms: int
    residual_rms: int


def estimate_residual(captured_rms: int, reference_rms: int, *, echo_gain: float) -> ResidualEstimate:
    """Conservative scalar residual pending final installed-geometry calibration."""
    if captured_rms < 0 or reference_rms < 0 or echo_gain < 0:
        raise ValueError("acoustic values must be non-negative")
    residual = max(0, round(captured_rms - reference_rms * echo_gain))
    return ResidualEstimate(captured_rms, reference_rms, residual)


def estimate_delay_ms(
    captured: list[int], reference: list[int], *, frame_ms: int = 30, maximum_delay_ms: int = 900
) -> int:
    """Choose the non-negative lag with greatest energy-shape correlation."""
    if len(captured) != len(reference) or len(captured) < 3:
        raise ValueError("captured and reference frames must have equal length of at least three")
    maximum_frames = min(maximum_delay_ms // frame_ms, len(captured) - 2)
    best_delay, best_score = 0, float("-inf")
    for delay in range(maximum_frames + 1):
        left, right = captured[delay:], reference[:len(reference) - delay]
        mean_left, mean_right = sum(left) / len(left), sum(right) / len(right)
        score = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
        if score > best_score:
            best_delay, best_score = delay, score
    return best_delay * frame_ms


@dataclass(frozen=True)
class ReferenceAlignment:
    delay_ms: int
    echo_gain: float
    confident: bool

    def residual(self, captured_rms: int, reference_rms: int) -> ResidualEstimate | None:
        if not self.confident:
            return None
        return estimate_residual(captured_rms, reference_rms, echo_gain=self.echo_gain)


def estimate_echo_gain(captured: list[int], reference: list[int]) -> float | None:
    """Robust energy-ratio estimate; refuses silent or mismatched fixtures."""
    if len(captured) != len(reference) or not captured:
        return None
    pairs = [(c, r) for c, r in zip(captured, reference) if r >= 100]
    if len(pairs) < 3:
        return None
    ratios = sorted(c / r for c, r in pairs)
    return ratios[len(ratios) // 2]
