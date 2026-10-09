from __future__ import annotations

import base64
import json
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

from .models import AmbientMood
from .state import AmbientMoodState, ConversationState

AMBIENT_SCHEMA_VERSION = 1
AMBIENT_AAD = b"frankenstein-creature-ambient:v1"
MIN_EPISODE = timedelta(hours=2)
MAX_EPISODE = timedelta(hours=8)


class AmbientStateCorrupt(RuntimeError):
    """The persisted ambient episode cannot be trusted."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AmbientEpisode:
    mood: AmbientMood
    started_at: datetime
    ends_at: datetime
    source: str
    sequence: int = 0

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("ambient episode timestamps must be timezone-aware")
        duration = self.ends_at - self.started_at
        if not MIN_EPISODE <= duration <= MAX_EPISODE:
            raise ValueError("ambient episode must last between two and eight hours")
        if not self.source.strip() or self.sequence < 0:
            raise ValueError("ambient episode source and sequence are invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "mood": self.mood.value,
            "started_at": self.started_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "source": self.source,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "AmbientEpisode":
        try:
            return cls(
                mood=AmbientMood(str(payload["mood"])),
                started_at=datetime.fromisoformat(str(payload["started_at"])),
                ends_at=datetime.fromisoformat(str(payload["ends_at"])),
                source=str(payload["source"]),
                sequence=int(payload.get("sequence", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AmbientStateCorrupt("ambient episode payload is invalid") from exc


@dataclass(frozen=True)
class EncryptedAmbientMoodStore:
    path: Path
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
            raise RuntimeError("ambient encryption key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise RuntimeError("ambient encryption key must decode to exactly 32 bytes")
        return key

    @staticmethod
    def _aesgcm(key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError("install the optional 'records' dependency") from exc
        return AESGCM(key)

    def read(self) -> AmbientEpisode:
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            if envelope.get("version") != AMBIENT_SCHEMA_VERSION or envelope.get("algorithm") != "AES-256-GCM":
                raise AmbientStateCorrupt("unsupported ambient state envelope")
            nonce = base64.urlsafe_b64decode(envelope["nonce"])
            ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
            plaintext = self._aesgcm(self._key()).decrypt(nonce, ciphertext, AMBIENT_AAD)
            return AmbientEpisode.from_dict(json.loads(plaintext))
        except FileNotFoundError:
            raise
        except AmbientStateCorrupt:
            raise
        except Exception as exc:
            raise AmbientStateCorrupt("ambient state authentication failed") from exc

    def write(self, episode: AmbientEpisode) -> None:
        key = self._key()
        nonce = os.urandom(12)
        ciphertext = self._aesgcm(key).encrypt(
            nonce,
            json.dumps(episode.to_dict(), separators=(",", ":")).encode("utf-8"),
            AMBIENT_AAD,
        )
        envelope = json.dumps(
            {
                "version": AMBIENT_SCHEMA_VERSION,
                "algorithm": "AES-256-GCM",
                "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".ambient-", dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if os.path.exists(temporary):
                os.unlink(temporary)


class AmbientMoodScheduler:
    """Persisted, bounded ambient mood with an authored time-based bias."""

    def __init__(
        self,
        store: EncryptedAmbientMoodStore,
        *,
        clock: Callable[[], datetime] = utc_now,
        seed: str = "creature-ambient-v1",
    ) -> None:
        self.store = store
        self.clock = clock
        self.seed = seed

    @staticmethod
    def _weights(now: datetime) -> dict[AmbientMood, float]:
        hour = now.hour
        if 6 <= hour < 10:
            return {
                AmbientMood.DORMANT: 0.20,
                AmbientMood.LONELY: 0.12,
                AmbientMood.RESTLESS: 0.12,
                AmbientMood.GUARDED: 0.10,
                AmbientMood.HOPEFUL: 0.40,
                AmbientMood.AGITATED: 0.06,
            }
        if 10 <= hour < 17:
            return {
                AmbientMood.DORMANT: 0.10,
                AmbientMood.LONELY: 0.18,
                AmbientMood.RESTLESS: 0.22,
                AmbientMood.GUARDED: 0.16,
                AmbientMood.HOPEFUL: 0.24,
                AmbientMood.AGITATED: 0.10,
            }
        if 17 <= hour < 23:
            return {
                AmbientMood.DORMANT: 0.08,
                AmbientMood.LONELY: 0.28,
                AmbientMood.RESTLESS: 0.16,
                AmbientMood.GUARDED: 0.22,
                AmbientMood.HOPEFUL: 0.14,
                AmbientMood.AGITATED: 0.12,
            }
        return {
            AmbientMood.DORMANT: 0.32,
            AmbientMood.LONELY: 0.24,
            AmbientMood.RESTLESS: 0.14,
            AmbientMood.GUARDED: 0.16,
            AmbientMood.HOPEFUL: 0.06,
            AmbientMood.AGITATED: 0.08,
        }

    def _rng(self, now: datetime, sequence: int) -> random.Random:
        return random.Random(f"{self.seed}|{now.date().isoformat()}|{now.hour}|{sequence}")

    def _new_episode(
        self,
        now: datetime,
        sequence: int,
        previous: AmbientEpisode | None,
        *,
        recovery: bool = False,
    ) -> AmbientEpisode:
        if recovery:
            mood = AmbientMood.DORMANT
            source = "recovery"
            duration_minutes = 240
        else:
            rng = self._rng(now, sequence)
            weights = self._weights(now)
            if previous is not None:
                weights = {mood: weight for mood, weight in weights.items() if mood != previous.mood}
            moods, values = tuple(weights), tuple(weights.values())
            mood = rng.choices(moods, weights=values, k=1)[0]
            duration_minutes = rng.randint(120, 480)
            source = "time_schedule"
        return AmbientEpisode(
            mood=mood,
            started_at=now,
            ends_at=now + timedelta(minutes=duration_minutes),
            source=source,
            sequence=sequence,
        )

    def current(self) -> AmbientEpisode:
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("ambient scheduler clock must return a timezone-aware datetime")
        previous: AmbientEpisode | None = None
        recovery = False
        try:
            previous = self.store.read()
        except FileNotFoundError:
            pass
        except AmbientStateCorrupt:
            recovery = True
        if previous is not None and previous.started_at <= now < previous.ends_at:
            return previous
        sequence = (previous.sequence + 1) if previous is not None else 0
        episode = self._new_episode(now, sequence, previous, recovery=recovery)
        self.store.write(episode)
        return episode

    def apply_to(self, state: ConversationState) -> AmbientEpisode:
        episode = self.current()
        state.ambient = AmbientMoodState(
            mood=episode.mood,
            source=episode.source,
            updated_at=episode.started_at.isoformat(),
        )
        return episode
