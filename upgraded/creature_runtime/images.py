from __future__ import annotations

import base64
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


IMAGE_SCHEMA_VERSION = 1
IMAGE_ASSOCIATED_DATA_PREFIX = b"frankenstein-creature-still:v1:"
DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024
_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")
_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


@dataclass(frozen=True)
class StillImage:
    data: bytes
    media_type: str


@dataclass(frozen=True)
class EncryptedStillImageStore:
    directory: Path
    key_env: str = "CREATURE_RECORD_KEY"
    key_provider: Callable[[str], str] | None = None
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES

    def __post_init__(self) -> None:
        if self.max_image_bytes < 1:
            raise ValueError("maximum image size must be positive")

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
            raise RuntimeError("still-image encryption key is not valid URL-safe base64") from exc
        if len(key) != 32:
            raise RuntimeError("still-image encryption key must decode to exactly 32 bytes")
        return key

    @staticmethod
    def _aesgcm(key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError("install the optional 'records' dependency") from exc
        return AESGCM(key)

    def _path(self, record_id: str) -> Path:
        if not _SAFE_ID.fullmatch(record_id):
            raise ValueError("record id contains unsafe characters")
        return self.directory / f"{record_id}.cimage"

    def _validate(self, image: StillImage) -> None:
        if image.media_type not in _MAGIC:
            raise ValueError("still image must be JPEG or PNG")
        if not image.data:
            raise ValueError("still image must not be empty")
        if len(image.data) > self.max_image_bytes:
            raise ValueError("still image exceeds configured size limit")
        if not any(image.data.startswith(magic) for magic in _MAGIC[image.media_type]):
            raise ValueError("still image content does not match its media type")

    def write(self, record_id: str, image: StillImage) -> Path:
        destination = self._path(record_id)
        self._validate(image)
        nonce = os.urandom(12)
        associated_data = IMAGE_ASSOCIATED_DATA_PREFIX + record_id.encode("ascii")
        ciphertext = self._aesgcm(self._key()).encrypt(nonce, image.data, associated_data)
        envelope = json.dumps(
            {
                "version": IMAGE_SCHEMA_VERSION,
                "algorithm": "AES-256-GCM",
                "media_type": image.media_type,
                "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")

        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".image-", dir=self.directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary_name, destination)
            os.unlink(temporary_name)
            os.chmod(destination, 0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return destination

    def read(self, record_id: str) -> StillImage:
        envelope = json.loads(self._path(record_id).read_text(encoding="utf-8"))
        if (
            envelope.get("version") != IMAGE_SCHEMA_VERSION
            or envelope.get("algorithm") != "AES-256-GCM"
            or envelope.get("media_type") not in _MAGIC
        ):
            raise RuntimeError("unsupported still-image envelope")
        try:
            nonce = base64.urlsafe_b64decode(envelope["nonce"])
            ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
            associated_data = IMAGE_ASSOCIATED_DATA_PREFIX + record_id.encode("ascii")
            plaintext = self._aesgcm(self._key()).decrypt(nonce, ciphertext, associated_data)
        except Exception as exc:
            raise RuntimeError("still-image authentication failed") from exc
        image = StillImage(plaintext, envelope["media_type"])
        self._validate(image)
        return image

    def delete(self, record_id: str) -> bool:
        try:
            self._path(record_id).unlink()
            return True
        except FileNotFoundError:
            return False

