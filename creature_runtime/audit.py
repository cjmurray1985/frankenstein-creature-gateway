from __future__ import annotations

import base64
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


AUDIT_ASSOCIATED_DATA = b"frankenstein-creature-audit:v1"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    occurred_at: str
    actor: str
    action: str
    resource: str
    outcome: str


@dataclass(frozen=True)
class EncryptedAuditLog:
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
            raise RuntimeError("audit encryption key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise RuntimeError("audit encryption key must decode to exactly 32 bytes")
        return key

    @staticmethod
    def _aesgcm(key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError("install the optional 'records' dependency") from exc
        return AESGCM(key)

    def record(self, actor: str, action: str, resource: str, outcome: str) -> AuditEvent:
        values = (actor, action, resource, outcome)
        if any(not value or len(value) > 256 for value in values):
            raise ValueError("audit fields must contain 1 to 256 characters")
        event = AuditEvent(
            str(uuid.uuid4()),
            datetime.now(timezone.utc).isoformat(),
            actor,
            action,
            resource,
            outcome,
        )
        plaintext = json.dumps(asdict(event), separators=(",", ":")).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self._aesgcm(self._key()).encrypt(nonce, plaintext, AUDIT_ASSOCIATED_DATA)
        envelope = json.dumps(
            {
                "version": 1,
                "algorithm": "AES-256-GCM",
                "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        destination = self.directory / f"{event.occurred_at.replace(':', '')}-{event.event_id}.caudit"
        descriptor, temporary_name = tempfile.mkstemp(prefix=".audit-", dir=self.directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary_name, destination)
            os.unlink(temporary_name)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return event

    def read_all(self) -> list[AuditEvent]:
        if not self.directory.exists():
            return []
        events = []
        for path in sorted(self.directory.glob("*.caudit")):
            envelope = json.loads(path.read_text(encoding="utf-8"))
            try:
                nonce = base64.urlsafe_b64decode(envelope["nonce"])
                ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
                plaintext = self._aesgcm(self._key()).decrypt(
                    nonce, ciphertext, AUDIT_ASSOCIATED_DATA
                )
                events.append(AuditEvent(**json.loads(plaintext)))
            except Exception as exc:
                raise RuntimeError("audit record authentication failed") from exc
        return events

