from __future__ import annotations

from dataclasses import dataclass

from .models import MotionIntent, MotionRequest


@dataclass(frozen=True)
class SafeMotionRequestAdapter:
    """Emits intent records only. It has no GPIO, SSH, or subprocess capability."""

    allowed: frozenset[MotionIntent] = frozenset(
        {MotionIntent.STILL_LISTENING, MotionIntent.WITHDRAW_GAZE, MotionIntent.FACTORY_V1}
    )

    def request(self, intent: MotionIntent, *, dry_run: bool) -> MotionRequest:
        accepted = intent in self.allowed
        detail = (
            "request recorded; no hardware transport exists"
            if accepted
            else "request rejected: intent is not allowlisted"
        )
        return MotionRequest(intent, type(self).__name__, dry_run, accepted, detail)

