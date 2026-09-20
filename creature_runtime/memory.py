from __future__ import annotations

import base64
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MEMORY_AAD = b"frankenstein-creature-individual-memory:v1"
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass(frozen=True)
class MemoryFact:
    text: str
    source_record_id: str
    confidence: float
    created_at: str

    def __post_init__(self) -> None:
        if not self.text.strip() or not SAFE_ID.fullmatch(self.source_record_id):
            raise ValueError("memory fact requires text and a safe source record id")
        if not 0 <= self.confidence <= 1:
            raise ValueError("memory confidence must be between zero and one")


@dataclass(frozen=True)
class MemoryRetrieval:
    encounter_id: str
    recalled_source_record_ids: tuple[str, ...]
    created_at: str

    def __post_init__(self) -> None:
        if not SAFE_ID.fullmatch(self.encounter_id):
            raise ValueError("memory retrieval requires a safe encounter id")
        if any(not SAFE_ID.fullmatch(item) for item in self.recalled_source_record_ids):
            raise ValueError("memory retrieval contains an unsafe source record id")


@dataclass(frozen=True)
class IndividualMemoryStore:
    directory: Path
    key_env: str = "CREATURE_RECORD_KEY"
    key_provider: Callable[[str], str] | None = None

    def _key(self) -> bytes:
        encoded = (self.key_provider(self.key_env) if self.key_provider else os.getenv(self.key_env, "")).strip()
        try:
            key = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True) if encoded else b""
        except Exception as exc:
            raise RuntimeError("individual memory key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise RuntimeError("individual memory requires a 256-bit record key")
        return key

    def _path(self, participant_id: str) -> Path:
        if not SAFE_ID.fullmatch(participant_id):
            raise ValueError("unsafe participant id")
        return self.directory / f"{participant_id}.cmemory"

    @staticmethod
    def _aes(key: bytes):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(key)

    def _read_profile(self, participant_id: str) -> tuple[list[MemoryFact], list[MemoryRetrieval]]:
        path = self._path(participant_id)
        if not path.exists():
            return [], []
        envelope = json.loads(path.read_text())
        if envelope.get("version") != 1 or envelope.get("algorithm") != "AES-256-GCM":
            raise RuntimeError("unsupported individual memory envelope")
        try:
            plain = self._aes(self._key()).decrypt(
                base64.urlsafe_b64decode(envelope["nonce"]),
                base64.urlsafe_b64decode(envelope["ciphertext"]),
                MEMORY_AAD + participant_id.encode(),
            )
        except Exception as exc:
            raise RuntimeError("individual memory authentication failed") from exc
        profile = json.loads(plain)
        facts = [MemoryFact(**item) for item in profile["facts"]]
        retrievals = [
            MemoryRetrieval(
                encounter_id=item["encounter_id"],
                recalled_source_record_ids=tuple(item["recalled_source_record_ids"]),
                created_at=item["created_at"],
            )
            for item in profile.get("retrievals", [])
        ]
        return facts, retrievals

    def read(self, participant_id: str) -> list[MemoryFact]:
        """Administrative read. Runtime recall should use recall() so it is audited."""
        return self._read_profile(participant_id)[0]

    def retrievals(self, participant_id: str) -> list[MemoryRetrieval]:
        return self._read_profile(participant_id)[1]

    def recall(self, participant_id: str, encounter_id: str) -> list[MemoryFact]:
        facts, retrievals = self._read_profile(participant_id)
        if not facts:
            return []
        retrievals.append(MemoryRetrieval(
            encounter_id=encounter_id,
            recalled_source_record_ids=tuple(sorted({fact.source_record_id for fact in facts})),
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        self._write_profile(participant_id, facts, retrievals[-100:])
        return facts

    def _write_profile(
        self,
        participant_id: str,
        facts: list[MemoryFact],
        retrievals: list[MemoryRetrieval],
    ) -> Path:
        path = self._path(participant_id)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        nonce = os.urandom(12)
        plain = json.dumps({
            "participant_id": participant_id,
            "facts": [asdict(f) for f in facts],
            "retrievals": [asdict(item) for item in retrievals],
        }).encode()
        cipher = self._aes(self._key()).encrypt(nonce, plain, MEMORY_AAD + participant_id.encode())
        envelope = json.dumps({"version": 1, "algorithm": "AES-256-GCM",
                               "nonce": base64.urlsafe_b64encode(nonce).decode(),
                               "ciphertext": base64.urlsafe_b64encode(cipher).decode()}).encode()
        descriptor, temporary = tempfile.mkstemp(prefix=".memory-", dir=self.directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1; stream.write(envelope); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path); os.chmod(path, 0o600)
        finally:
            if descriptor >= 0: os.close(descriptor)
            if os.path.exists(temporary): os.unlink(temporary)
        return path

    def write(self, participant_id: str, facts: list[MemoryFact]) -> Path:
        """Replace facts while retaining the encrypted retrieval audit."""
        _, retrievals = self._read_profile(participant_id)
        return self._write_profile(participant_id, facts, retrievals)

    def remember(self, participant_id: str, fact: MemoryFact) -> Path:
        facts, retrievals = self._read_profile(participant_id)
        if not any(item.text.casefold() == fact.text.casefold() for item in facts):
            facts.append(fact)
        return self._write_profile(participant_id, facts[-24:], retrievals)

    def delete(self, participant_id: str) -> bool:
        try: self._path(participant_id).unlink(); return True
        except FileNotFoundError: return False


def extract_explicit_facts(visitor_text: str, record_id: str) -> list[MemoryFact]:
    """Extract only visitor-explicit names/promises; never infer demographics."""
    now = datetime.now(timezone.utc).isoformat()
    facts: list[MemoryFact] = []
    name = re.search(r"\bmy name is ([A-Za-z][A-Za-z' -]{0,39})", visitor_text, re.I)
    if name:
        facts.append(MemoryFact(f"The visitor said their name is {name.group(1).strip()}.", record_id, 1.0, now))
    for sentence in re.split(r"(?<=[.!?])\s+", visitor_text):
        if re.search(r"\b(?:I promise|I will|I'll|I shall)\b", sentence, re.I):
            facts.append(MemoryFact(f"The visitor said: {sentence.strip()}", record_id, 1.0, now))
    return facts
