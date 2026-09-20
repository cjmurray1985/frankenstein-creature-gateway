from __future__ import annotations

import threading
import time
import random
from dataclasses import dataclass
from pathlib import Path

from .models import Emotion


ACKNOWLEDGMENTS: dict[Emotion, tuple[str, str]] = {
    Emotion.DORMANT: ("i-wake-i-hear-you", "your-voice-has-reached-me"),
    Emotion.CURIOUS: ("let-me-consider", "your-question-is-not-small"),
    Emotion.HOPEFUL: ("i-hear-kindness", "stay-i-would-answer"),
    Emotion.ENGAGED: ("your-thought-has-reached-me", "i-follow-you"),
    Emotion.WARY: ("i-consider-your-purpose", "speak-plainly"),
    Emotion.HURT: ("though-the-words-wound", "give-me-a-moment"),
    Emotion.ANGRY: ("take-care", "do-not-press-further"),
    Emotion.WITHDRAWN: ("let-me-gather-what-remains", "i-am-not-yet-silent"),
}

BREATHS = (
    "breath-constrained.mp3",
    "breath-drawn.mp3",
    "breath-shuddering.mp3",
    "breath-caught.mp3",
    "breath-failing.mp3",
    "breath-hollow.mp3",
    "breath-staggered.mp3",
    "breath-held.mp3",
    "breath-fractured.mp3",
    "breath-thin.mp3",
    "breath-weighted.mp3",
    "breath-trembling.mp3",
    "breath-recovering.mp3",
    "breath-sunken.mp3",
    "breath-suppressed.mp3",
)

BRIDGES = (
    "bridge-low-murmur.mp3",
    "bridge-breath-catch.mp3",
    "bridge-drawn-exhale.mp3",
    "bridge-gathering.mp3",
)

SOMATIC_TEXTURES = (
    "body-muffled-heart.mp3",
    "body-throat-catch.mp3",
    "body-chest-resonance.mp3",
    "body-weight-settle.mp3",
    "body-pulse-tremor.mp3",
    "body-breath-residue.mp3",
)

# These deliberately avoid committing to an emotional interpretation before
# the response generator has completed its deeper reading of the turn.
NEUTRAL_ACKNOWLEDGMENTS = (
    "curious-let-me-consider.mp3",
    "dormant-your-voice-has-reached-me.mp3",
)


class _StoppedSession:
    def handoff(self) -> None:
        return None

    def stop(self) -> None:
        return None


@dataclass
class _ThreadSession:
    cancel_event: threading.Event
    reply_ready_event: threading.Event
    thread: threading.Thread

    def handoff(self) -> None:
        self.reply_ready_event.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            self.stop()

    def stop(self) -> None:
        self.cancel_event.set()
        self.thread.join(timeout=2)


@dataclass
class LocalLatencyMasker:
    cue_directory: Path
    player: object
    acknowledgment_delay_seconds: float = 3.0
    post_acknowledgment_pause_seconds: float = 2.0
    spoken_acknowledgments: bool = False
    _indices: dict[Emotion, int] | None = None
    _breath_index: int = 0
    _bridge_index: int = 0
    _acknowledgment_index: int = 0
    _breath_order: tuple[str, ...] | None = None
    _ambient_index: int = 0

    def __post_init__(self) -> None:
        if self._indices is None:
            self._indices = {}
        if self._breath_order is None:
            self._breath_order = tuple(random.SystemRandom().sample(BREATHS, len(BREATHS)))

    def _next_breath(self) -> Path:
        assert self._breath_order is not None
        name = self._breath_order[self._breath_index % len(self._breath_order)]
        self._breath_index += 1
        return self.cue_directory / name

    def _next_ambient(self) -> Path:
        name = SOMATIC_TEXTURES[self._ambient_index % len(SOMATIC_TEXTURES)]
        self._ambient_index += 1
        return self.cue_directory / name

    def begin(self, emotion: Emotion):
        breath = self._next_breath()
        bridge = self.cue_directory / BRIDGES[self._bridge_index % len(BRIDGES)]
        self._bridge_index += 1
        acknowledgment = None
        if (self.spoken_acknowledgments and
                self._acknowledgment_index < len(NEUTRAL_ACKNOWLEDGMENTS)):
            acknowledgment = self.cue_directory / NEUTRAL_ACKNOWLEDGMENTS[
                self._acknowledgment_index
            ]
            self._acknowledgment_index += 1
        if (not breath.is_file() or not bridge.is_file() or
                not all((self.cue_directory / name).is_file() for name in SOMATIC_TEXTURES) or
                (acknowledgment is not None and not acknowledgment.is_file())):
            return _StoppedSession()

        cancel = threading.Event()
        reply_ready = threading.Event()

        def run() -> None:
            started = time.monotonic()
            current_breath = breath
            # Breathing carries the ordinary delay. A breath already in progress
            # finishes naturally; if the reply becomes ready, no stock phrase is
            # inserted merely because a timer expired.
            while time.monotonic() - started < self.acknowledgment_delay_seconds:
                self.player.play_until(current_breath, cancel)
                if reply_ready.is_set() or cancel.is_set():
                    return
                current_breath = self._next_breath()
            if reply_ready.is_set() or cancel.is_set():
                return
            if acknowledgment is None:
                # With language disabled, never expose a hard software gap.
                # Sparse machinery sits between complete, varied breaths.
                while not reply_ready.is_set() and not cancel.is_set():
                    self.player.play_until(self._next_ambient(), cancel)
                    if reply_ready.is_set() or cancel.is_set():
                        return
                    self.player.play_until(self._next_breath(), cancel)
                return
            self.player.play_until(acknowledgment, cancel)
            if cancel.is_set():
                return
            # A short silence reads as thought, not failure. Only add another
            # vocal gesture when generation exceeds this natural pause.
            if reply_ready.wait(self.post_acknowledgment_pause_seconds):
                return
            self.player.play_until(bridge, cancel)
            while not reply_ready.is_set() and not cancel.is_set():
                continuation = self._next_breath()
                self.player.play_until(continuation, cancel)

        thread = threading.Thread(target=run, name="creature-latency-mask", daemon=True)
        thread.start()
        return _ThreadSession(cancel, reply_ready, thread)
