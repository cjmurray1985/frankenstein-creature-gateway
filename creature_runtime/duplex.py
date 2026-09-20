from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from .acoustic_reference import ReferenceAlignment


@dataclass(frozen=True)
class AcousticBargeInProfile:
    """Ephemeral calibration for the environment currently hosting the Creature."""

    ambient_rms: int
    self_echo_rms: int
    threshold: int
    enabled: bool
    reason: str

    @classmethod
    def derive(cls, *, ambient_rms: int, self_echo_rms: int,
               expected_voice_rms: int, minimum_margin: int = 800) -> "AcousticBargeInProfile":
        if min(ambient_rms, self_echo_rms, expected_voice_rms) < 0:
            raise ValueError("acoustic measurements must be non-negative")
        floor = max(ambient_rms, self_echo_rms)
        threshold = floor + minimum_margin
        if expected_voice_rms <= threshold:
            return cls(ambient_rms, self_echo_rms, threshold, False,
                       "near-end voice does not safely separate from present acoustic floor")
        return cls(ambient_rms, self_echo_rms, threshold, True, "calibrated for current environment")


@dataclass
class AdaptiveAcousticFloor:
    """Rolling, prompt-free acoustic estimates for changing public environments."""

    minimum_margin: int = 800
    ambient_rms: float = 0.0
    echo_rms: float = 0.0

    def observe(self, rms: int, *, creature_is_speaking: bool) -> AcousticBargeInProfile:
        if rms < 0:
            raise ValueError("RMS must be non-negative")
        # A slow rise avoids promoting a passing transient into the baseline;
        # a faster fall lets the Creature recover after it has passed.
        current = self.echo_rms if creature_is_speaking else self.ambient_rms
        alpha = .08 if rms > current else .22
        updated = current + alpha * (rms - current)
        if creature_is_speaking:
            self.echo_rms = updated
        else:
            self.ambient_rms = updated
        floor = max(self.ambient_rms, self.echo_rms)
        threshold = int(floor + self.minimum_margin)
        return AcousticBargeInProfile(
            int(self.ambient_rms), int(self.echo_rms), threshold,
            True, "rolling acoustic estimate; gate requires near-end speech evidence",
        )


@dataclass(frozen=True)
class BargeInDecision:
    detected_at_ms: int
    speech_started_at_ms: int
    preroll_from_ms: int


class CalibratedBargeInGate:
    """Gate near-end speech in the ReSpeaker's echo-cancelled capture.

    It has no playback or hardware capability. Callers must keep barge-in
    disabled unless their room calibration proves the configured residual
    threshold separates loudspeaker echo from near-end speech.
    """

    def __init__(self, *, threshold: int, minimum_voice_ms: int = 300,
                 frame_ms: int = 30, preroll_ms: int = 300,
                 required_active_ms: int = 180, evidence_window_ms: int = 1500) -> None:
        if threshold <= 0 or minimum_voice_ms < frame_ms or preroll_ms < 0:
            raise ValueError("invalid barge-in gate calibration")
        self.threshold = threshold
        self.minimum_voice_ms = minimum_voice_ms
        self.required_active_frames = (required_active_ms + frame_ms - 1) // frame_ms
        self.evidence_window_ms = evidence_window_ms
        self.frame_ms = frame_ms
        self.preroll_ms = preroll_ms
        self.active_at: list[int] = []
        self.triggered = False

    def observe(self, rms: int, *, at_ms: int) -> BargeInDecision | None:
        if self.triggered:
            return None
        if rms >= self.threshold:
            self.active_at.append(at_ms)
        cutoff = at_ms - self.evidence_window_ms
        self.active_at = [stamp for stamp in self.active_at if stamp >= cutoff]
        started_at_ms = self.active_at[0] if self.active_at else None
        span = 0 if started_at_ms is None else at_ms - started_at_ms + self.frame_ms
        if (rms < self.threshold or len(self.active_at) < self.required_active_frames
                or span < self.minimum_voice_ms):
            return None
        self.triggered = True
        assert started_at_ms is not None
        return BargeInDecision(
            detected_at_ms=at_ms,
            speech_started_at_ms=started_at_ms,
            preroll_from_ms=max(0, started_at_ms - self.preroll_ms),
        )


@dataclass
class BargeInSupervisor:
    """Connect a calibrated near-end gate to reply cancellation.

    The supervisor intentionally knows nothing about ALSA, GPIO, or motion.
    A live capture loop supplies residual RMS frames from the ReSpeaker; only a
    calibrated decision may cancel the currently audible reply.
    """

    gate: CalibratedBargeInGate
    interrupt_reply: Callable[[], None]
    last_decision: BargeInDecision | None = None

    def observe_residual(self, rms: int, *, at_ms: int) -> BargeInDecision | None:
        decision = self.gate.observe(rms, at_ms=at_ms)
        if decision is not None:
            self.last_decision = decision
            self.interrupt_reply()
        return decision

    def observe_reference_aligned(
        self, captured_rms: int, reference_rms: int, alignment: ReferenceAlignment, *, at_ms: int
    ) -> BargeInDecision | None:
        """Use AEC residual only when an external alignment has earned confidence."""
        estimate = alignment.residual(captured_rms, reference_rms)
        if estimate is None:
            return None
        return self.observe_residual(estimate.residual_rms, at_ms=at_ms)
