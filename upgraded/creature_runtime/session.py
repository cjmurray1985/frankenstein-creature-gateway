from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Callable, Protocol

from .images import StillImage
from .models import CreatureTurn, Emotion
from .records import ConversationArchiveSession, ConversationRecord, ParticipantRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationWriter(Protocol):
    def write(self, record: ConversationRecord) -> Path: ...


class StillImageWriter(Protocol):
    def write(self, record_id: str, image: StillImage) -> Path: ...
    def delete(self, record_id: str) -> bool: ...


def summarize_emotions(emotions: list[Emotion]) -> str:
    """Return a deterministic, private-dashboard summary of the emotional arc."""
    if not emotions:
        raise ValueError("cannot summarize an empty conversation")
    first, last = emotions[0], emotions[-1]
    dominant = Counter(emotions).most_common(1)[0][0]
    if first is last:
        return f"The Creature remained chiefly {dominant.value}."
    return (
        f"The Creature moved from {first.value} toward {last.value}; "
        f"the exchange was chiefly {dominant.value}."
    )


@dataclass
class ConversationSessionController:
    store: ConversationWriter
    participants: tuple[ParticipantRecord, ...]
    idle_timeout: timedelta = timedelta(seconds=45)
    maximum_duration: timedelta = timedelta(minutes=20)
    still_image_path: str | None = None
    image_store: StillImageWriter | None = None
    notice_present: bool = True
    clock: Callable[[], datetime] = utc_now
    archive: ConversationArchiveSession | None = None
    _last_activity: datetime = field(init=False, repr=False)
    _in_flight: int = field(default=0, init=False, repr=False)
    _finished: ConversationRecord | None = field(default=None, init=False, repr=False)
    _emotions: list[Emotion] = field(default_factory=list, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.participants:
            raise ValueError("a conversation requires at least one participant")
        if self.idle_timeout <= timedelta(0) or self.maximum_duration <= timedelta(0):
            raise ValueError("session timeouts must be positive")
        now = self.clock()
        self.archive = self.archive or ConversationArchiveSession(started_at=now)
        self._last_activity = now

    @property
    def active(self) -> bool:
        return self._finished is None

    def begin_turn(self, *, at: datetime | None = None) -> None:
        with self._lock:
            self._require_active()
            self._in_flight += 1
            self._last_activity = at or self.clock()

    def complete_turn(
        self, turn: CreatureTurn, speaker_id: str, *, at: datetime | None = None
    ) -> None:
        with self._lock:
            self._require_active()
            if self._in_flight < 1:
                raise RuntimeError("complete_turn requires a matching begin_turn")
            if speaker_id not in {participant.participant_id for participant in self.participants}:
                raise ValueError("turn speaker must match a session participant")
            assert self.archive is not None
            self.archive.append(turn, speaker_id)
            self._emotions.append(turn.emotion)
            self._in_flight -= 1
            self._last_activity = at or self.clock()

    def abandon_turn(self, *, at: datetime | None = None) -> None:
        with self._lock:
            self._require_active()
            if self._in_flight < 1:
                raise RuntimeError("abandon_turn requires a matching begin_turn")
            self._in_flight -= 1
            self._last_activity = at or self.clock()

    def tick(self, *, at: datetime | None = None) -> ConversationRecord | None:
        """Finalize after idle/absolute timeout, but never during an active turn."""
        with self._lock:
            if self._finished is not None or self._in_flight:
                return self._finished
            now = at or self.clock()
            assert self.archive is not None
            idle = now - self._last_activity >= self.idle_timeout
            expired = now - self.archive.started_at >= self.maximum_duration
            return self._finalize(now, None) if idle or expired else None

    def end(
        self, *, at: datetime | None = None, still_image: StillImage | None = None
    ) -> ConversationRecord | None:
        """Explicitly finish a conversation; an in-flight turn must settle first."""
        with self._lock:
            if self._finished is not None:
                return self._finished
            if self._in_flight:
                raise RuntimeError("cannot end a conversation while a turn is in flight")
            return self._finalize(at or self.clock(), still_image)

    def _finalize(
        self, ended_at: datetime, still_image: StillImage | None
    ) -> ConversationRecord | None:
        if not self._emotions:
            return None
        assert self.archive is not None
        if still_image is not None and self.image_store is None:
            raise RuntimeError("still image supplied without an encrypted image store")
        image_written = False
        image_path = self.still_image_path
        if still_image is not None:
            assert self.image_store is not None
            stored = self.image_store.write(self.archive.record_id, still_image)
            image_written = True
            image_path = stored.name
        try:
            record = self.archive.finalize(
                self.participants,
                summarize_emotions(self._emotions),
                still_image_path=image_path,
                notice_present=self.notice_present,
                ended_at=ended_at,
            )
            self.store.write(record)
        except BaseException:
            if image_written:
                assert self.image_store is not None
                self.image_store.delete(self.archive.record_id)
            raise
        self._finished = record
        return record

    def _require_active(self) -> None:
        if self._finished is not None:
            raise RuntimeError("conversation has already ended")
