from __future__ import annotations

import base64
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")
_AAD_PREFIX = b"frankenstein-creature-speech:v1:"


@dataclass(frozen=True)
class EncryptedSpeechStore:
    directory: Path
    key_env: str = "CREATURE_RECORD_KEY"

    def _path(self, record_id: str) -> Path:
        if not _SAFE_ID.fullmatch(record_id):
            raise ValueError("record id contains unsafe characters")
        return self.directory / f"{record_id}.cspeech"

    def _key(self) -> bytes:
        try:
            key = base64.b64decode(os.environ.get(self.key_env, "").strip(), altchars=b"-_", validate=True)
        except Exception as exc:
            raise RuntimeError("speech encryption key is invalid") from exc
        if len(key) != 32:
            raise RuntimeError("speech encryption key must decode to 32 bytes")
        return key

    def validate_key(self) -> None:
        self._key()

    @staticmethod
    def _aes(key: bytes):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(key)

    def exists(self, record_id: str) -> bool:
        return self._path(record_id).is_file()

    def write(self, record_id: str, data: bytes) -> Path:
        if not data or not data.startswith(b"ID3"):
            raise ValueError("archived speech must be an ID3-tagged MP3")
        nonce = os.urandom(12)
        ciphertext = self._aes(self._key()).encrypt(nonce, data, _AAD_PREFIX + record_id.encode("ascii"))
        envelope = json.dumps({"version": 1, "algorithm": "AES-256-GCM", "media_type": "audio/mpeg",
            "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
            "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii")}, separators=(",", ":")).encode()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".speech-", dir=self.directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(envelope); stream.flush(); os.fsync(stream.fileno())
            os.link(temporary, self._path(record_id)); os.unlink(temporary)
            os.chmod(self._path(record_id), 0o600)
        finally:
            if descriptor >= 0: os.close(descriptor)
            if os.path.exists(temporary): os.unlink(temporary)
        return self._path(record_id)

    def read(self, record_id: str) -> bytes:
        envelope = json.loads(self._path(record_id).read_text())
        if envelope.get("version") != 1 or envelope.get("algorithm") != "AES-256-GCM" or envelope.get("media_type") != "audio/mpeg":
            raise RuntimeError("unsupported speech envelope")
        try:
            return self._aes(self._key()).decrypt(base64.urlsafe_b64decode(envelope["nonce"]),
                base64.urlsafe_b64decode(envelope["ciphertext"]), _AAD_PREFIX + record_id.encode("ascii"))
        except Exception as exc:
            raise RuntimeError("speech authentication failed") from exc

    def delete(self, record_id: str) -> bool:
        try: self._path(record_id).unlink(); return True
        except FileNotFoundError: return False
