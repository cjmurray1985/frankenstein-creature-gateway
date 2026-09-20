from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class Emotion(str, Enum):
    DORMANT = "dormant"
    CURIOUS = "curious"
    HOPEFUL = "hopeful"
    ENGAGED = "engaged"
    WARY = "wary"
    HURT = "hurt"
    ANGRY = "angry"
    WITHDRAWN = "withdrawn"


class MotionIntent(str, Enum):
    STILL_LISTENING = "still_listening"
    FACTORY_V1 = "factory_v1"
    WITHDRAW_GAZE = "withdraw_gaze"


@dataclass(frozen=True)
class VocalContext:
    audience_count: int = 1
    speaker_is_young: bool = False

    @property
    def crowd_mode(self) -> bool:
        return self.audience_count > 3


@dataclass(frozen=True)
class AudioTurn:
    path: Path
    started_seconds: float = 0.0
    ended_seconds: float | None = None


@dataclass(frozen=True)
class ReplyPlan:
    text: str
    emotion: Emotion
    motion: MotionIntent


@dataclass(frozen=True)
class StreamingReplyPlan:
    chunks: Iterable[str]
    emotion: Emotion
    motion: MotionIntent


@dataclass(frozen=True)
class MotionRequest:
    intent: MotionIntent
    adapter: str
    dry_run: bool
    accepted: bool
    detail: str


@dataclass(frozen=True)
class SpeechRequest:
    text: str
    adapter: str
    voice: str
    dry_run: bool
    output_path: str | None = None


@dataclass(frozen=True)
class CreatureTurn:
    visitor_text: str
    reply: str
    emotion: Emotion
    motion_request: MotionRequest
    speech_request: SpeechRequest

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
