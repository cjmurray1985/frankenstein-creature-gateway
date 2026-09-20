from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .models import AudioTurn, Emotion, MotionIntent, MotionRequest, ReplyPlan, SpeechRequest, StreamingReplyPlan, VocalContext
from .state import ConversationState


class AudioInput(Protocol):
    def capture(self) -> Path: ...


class TurnDetector(Protocol):
    def detect(self, audio_path: Path) -> AudioTurn | None: ...


class Transcriber(Protocol):
    def transcribe(self, audio: AudioTurn) -> str: ...


class ResponseGenerator(Protocol):
    def generate(self, visitor_text: str, state: ConversationState) -> ReplyPlan: ...


class StreamingResponseGenerator(Protocol):
    def generate_stream(self, visitor_text: str, state: ConversationState) -> StreamingReplyPlan: ...


class TextToSpeech(Protocol):
    def request(
        self, text: str, emotion: Emotion, *, dry_run: bool, context: VocalContext | None = None
    ) -> SpeechRequest: ...


class MotionOutput(Protocol):
    def request(self, intent: MotionIntent, *, dry_run: bool) -> MotionRequest: ...


class LatencyMaskSession(Protocol):
    def handoff(self) -> None: ...

    def stop(self) -> None: ...


class LatencyMasking(Protocol):
    def begin(self, emotion: Emotion) -> LatencyMaskSession: ...


class SpeechPlayback(Protocol):
    def start(self, path: Path) -> None: ...

    def crossfade_to(self, path: Path) -> None: ...

    def interrupt(self) -> None: ...


History = Sequence[tuple[str, str]]
