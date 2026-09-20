from __future__ import annotations

import base64
import json
import math
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .models import CreatureTurn, Emotion, MotionIntent


SCHEMA_VERSION = 1
ASSOCIATED_DATA = b"frankenstein-creature-conversation:v1"
_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class InferredAttribute:
    value: str
    confidence: float
    source: str = "vision_inference"

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("inferred attribute value must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("inferred attribute confidence must be between 0 and 1")


@dataclass(frozen=True)
class ParticipantRecord:
    participant_id: str
    temporary_label: str
    remembered_name: str | None = None
    creature_address: str | None = None
    inferred_age: InferredAttribute | None = None
    inferred_gender: InferredAttribute | None = None
    inferred_ethnicity: InferredAttribute | None = None
    facial_embedding: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if not self.participant_id.strip() or not self.temporary_label.strip():
            raise ValueError("participant id and temporary label must not be empty")
        if self.facial_embedding is not None:
            if not self.facial_embedding or len(self.facial_embedding) > 4096:
                raise ValueError("facial embedding must contain 1 to 4096 values")
            if not all(math.isfinite(value) for value in self.facial_embedding):
                raise ValueError("facial embedding values must be finite")


@dataclass(frozen=True)
class ArchivedTurn:
    speaker_id: str
    visitor_text: str
    creature_reply: str
    emotion: Emotion
    motion_intent: MotionIntent


@dataclass(frozen=True)
class ConversationRecord:
    record_id: str
    started_at: str
    ended_at: str
    participants: tuple[ParticipantRecord, ...]
    turns: tuple[ArchivedTurn, ...]
    emotional_summary: str
    group_size: int
    still_image_path: str | None = None
    notice_present: bool = True
    schema_version: int = SCHEMA_VERSION


@dataclass
class ConversationArchiveSession:
    started_at: datetime = field(default_factory=utc_now)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _turns: list[ArchivedTurn] = field(default_factory=list, init=False, repr=False)

    def append(self, turn: CreatureTurn, speaker_id: str) -> None:
        if not speaker_id.strip():
            raise ValueError("speaker_id must not be empty")
        self._turns.append(
            ArchivedTurn(
                speaker_id,
                turn.visitor_text,
                turn.reply,
                turn.emotion,
                turn.motion_request.intent,
            )
        )

    def finalize(
        self,
        participants: tuple[ParticipantRecord, ...],
        emotional_summary: str,
        *,
        still_image_path: str | None = None,
        notice_present: bool = True,
        ended_at: datetime | None = None,
    ) -> ConversationRecord:
        if not self._turns:
            raise ValueError("cannot archive a conversation without turns")
        if not participants:
            raise ValueError("cannot archive a conversation without participants")
        participant_ids = {participant.participant_id for participant in participants}
        if any(turn.speaker_id not in participant_ids for turn in self._turns):
            raise ValueError("every turn speaker must match an archived participant")
        if not emotional_summary.strip():
            raise ValueError("emotional summary must not be empty")
        finished = ended_at or utc_now()
        if finished < self.started_at:
            raise ValueError("conversation end must not precede its start")
        return ConversationRecord(
            record_id=self.record_id,
            started_at=self.started_at.isoformat(),
            ended_at=finished.isoformat(),
            participants=participants,
            turns=tuple(self._turns),
            emotional_summary=emotional_summary.strip(),
            group_size=len(participants),
            still_image_path=still_image_path,
            notice_present=notice_present,
        )


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported record value: {type(value).__name__}")


@dataclass(frozen=True)
class EncryptedConversationStore:
    directory: Path
    key_env: str = "CREATURE_RECORD_KEY"
    key_provider: Callable[[str], str] | None = None

    def _key(self) -> bytes:
        encoded = (
            self.key_provider(self.key_env)
            if self.key_provider is not None
            else os.environ.get(self.key_env, "")
        ).strip()
        if not encoded:
            raise RuntimeError(f"required encryption key is not set: {self.key_env}")
        try:
            key = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
        except Exception as exc:
            raise RuntimeError("conversation encryption key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise RuntimeError("conversation encryption key must decode to exactly 32 bytes")
        return key

    def _path(self, record_id: str) -> Path:
        if not _SAFE_ID.fullmatch(record_id):
            raise ValueError("record id contains unsafe characters")
        return self.directory / f"{record_id}.crecord"

    def validate_key(self) -> None:
        self._key()

    @staticmethod
    def _aesgcm(key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError("install the optional 'records' dependency") from exc
        return AESGCM(key)

    def write(self, record: ConversationRecord) -> Path:
        key = self._key()
        plaintext = json.dumps(
            asdict(record),
            default=_json_default,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self._aesgcm(key).encrypt(nonce, plaintext, ASSOCIATED_DATA)
        envelope = json.dumps(
            {
                "version": SCHEMA_VERSION,
                "algorithm": "AES-256-GCM",
                "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")

        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        destination = self._path(record.record_id)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".record-", dir=self.directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            # A finalized record is append-only. Hard-link publication is
            # atomic on this filesystem and refuses to replace an existing ID.
            os.link(temporary_name, destination)
            os.unlink(temporary_name)
            os.chmod(destination, 0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return destination

    def read(self, record_id: str) -> dict[str, Any]:
        envelope = json.loads(self._path(record_id).read_text(encoding="utf-8"))
        if envelope.get("version") != SCHEMA_VERSION or envelope.get("algorithm") != "AES-256-GCM":
            raise RuntimeError("unsupported conversation record envelope")
        try:
            nonce = base64.urlsafe_b64decode(envelope["nonce"])
            ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
            plaintext = self._aesgcm(self._key()).decrypt(nonce, ciphertext, ASSOCIATED_DATA)
        except Exception as exc:
            raise RuntimeError("conversation record authentication failed") from exc
        return json.loads(plaintext)

    def list_record_ids(self) -> list[str]:
        if not self.directory.exists():
            return []
        return sorted(path.stem for path in self.directory.glob("*.crecord"))

    def delete(self, record_id: str) -> bool:
        path = self._path(record_id)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
