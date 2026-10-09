from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .images import StillImage


class ConversationReader(Protocol):
    def list_record_ids(self) -> list[str]: ...
    def read(self, record_id: str) -> dict[str, Any]: ...
    def delete(self, record_id: str) -> bool: ...


class AttachmentDeleter(Protocol):
    def delete(self, record_id: str) -> bool: ...


class ImageReader(AttachmentDeleter, Protocol):
    def read(self, record_id: str) -> StillImage: ...


class SpeechReader(AttachmentDeleter, Protocol):
    def read(self, record_id: str) -> bytes: ...
    def exists(self, record_id: str) -> bool: ...


class RequestAuthenticator(Protocol):
    def authenticated(self, headers: Mapping[str, str]) -> bool: ...


class AuditWriter(Protocol):
    def record(self, actor: str, action: str, resource: str, outcome: str) -> object: ...


@dataclass(frozen=True)
class TailscaleServeAuthenticator:
    """Trust a Serve identity header only at a separately enforced loopback origin."""

    owner_login: str

    def __post_init__(self) -> None:
        if not self.owner_login or not self.owner_login.isascii():
            raise ValueError("Tailscale owner login must be non-empty ASCII")

    def authenticated(self, headers: Mapping[str, str]) -> bool:
        supplied = headers.get("tailscale-user-login", "")
        expected_digest = hashlib.sha256(self.owner_login.encode("ascii")).digest()
        supplied_digest = hashlib.sha256(supplied.encode("utf-8")).digest()
        return bool(supplied) and hmac.compare_digest(expected_digest, supplied_digest)


@dataclass(frozen=True)
class PrivateAPIResponse:
    status: int
    body: dict[str, Any] | bytes | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class PrivateConversationAPI:
    """Transport-neutral, default-deny boundary for a future private dashboard."""

    store: ConversationReader
    bearer_token: str = ""
    image_store: ImageReader | None = None
    speech_store: SpeechReader | None = None
    authenticator: RequestAuthenticator | None = None
    audit_log: AuditWriter | None = None

    def __post_init__(self) -> None:
        if bool(self.bearer_token) == bool(self.authenticator):
            raise ValueError("configure exactly one private dashboard authenticator")

    def handle(
        self, method: str, path: str, headers: Mapping[str, str] | None = None
    ) -> PrivateAPIResponse:
        normalized = {key.lower(): value for key, value in (headers or {}).items()}
        authenticated = (
            self.authenticator.authenticated(normalized)
            if self.authenticator is not None
            else self._bearer_authenticated(normalized.get("authorization", ""))
        )
        actor = normalized.get("tailscale-user-login", "development-bearer")[:256] or "unknown"
        if not authenticated:
            response_headers = {"Cache-Control": "no-store"}
            if self.authenticator is None:
                response_headers["WWW-Authenticate"] = "Bearer"
            response = PrivateAPIResponse(
                401,
                {"error": "unauthorized"},
                response_headers,
            )
            self._audit(actor, method.upper(), path, response.status)
            return response

        method = method.upper()
        response: PrivateAPIResponse
        if path == "/records" and method == "GET":
            response = self._list()
        elif path.startswith("/records/") and path.endswith("/audio") and path.count("/") == 3:
            record_id = path.removeprefix("/records/").removesuffix("/audio")
            response = self._read_audio(record_id) if method == "GET" else self._response(404, {"error": "not_found"})
        elif path.startswith("/records/") and path.endswith("/image") and path.count("/") == 3:
            record_id = path.removeprefix("/records/").removesuffix("/image")
            if method == "GET":
                response = self._read_image(record_id)
            else:
                response = self._response(404, {"error": "not_found"})
        elif path.startswith("/records/") and path.count("/") == 2:
            record_id = path.removeprefix("/records/")
            if method == "GET":
                response = self._read(record_id)
            elif method == "DELETE":
                response = self._delete(record_id, normalized)
            else:
                response = self._response(404, {"error": "not_found"})
        else:
            response = self._response(404, {"error": "not_found"})
        self._audit(actor, method, path, response.status)
        return response

    def _audit(self, actor: str, action: str, resource: str, status: int) -> None:
        if self.audit_log is not None:
            self.audit_log.record(actor, action, resource[:256] or "/", str(status))

    def _bearer_authenticated(self, authorization: str) -> bool:
        scheme, separator, supplied = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not supplied:
            return False
        expected_digest = hashlib.sha256(self.bearer_token.encode("utf-8")).digest()
        supplied_digest = hashlib.sha256(supplied.encode("utf-8")).digest()
        return hmac.compare_digest(expected_digest, supplied_digest)

    def _list(self) -> PrivateAPIResponse:
        records = []
        try:
            for record_id in self.store.list_record_ids():
                record = self.store.read(record_id)
                records.append(
                    {
                        "record_id": record["record_id"],
                        "started_at": record["started_at"],
                        "ended_at": record["ended_at"],
                        "group_size": record["group_size"],
                        "turn_count": len(record.get("turns", [])),
                        "emotional_summary": record["emotional_summary"],
                    }
                )
        except (RuntimeError, KeyError, TypeError):
            return self._response(500, {"error": "record_unavailable"})
        return self._response(200, {"records": records})

    def _read(self, record_id: str) -> PrivateAPIResponse:
        try:
            record = self.store.read(record_id)
            safe = dict(record)
            safe["participants"] = [self._safe_participant(item) for item in record["participants"]]
            safe["speech_audio_present"] = bool(self.speech_store and self.speech_store.exists(record_id))
        except (FileNotFoundError, ValueError):
            return self._response(404, {"error": "not_found"})
        except (RuntimeError, KeyError, TypeError):
            return self._response(500, {"error": "record_unavailable"})
        return self._response(200, {"record": safe})

    def _delete(self, record_id: str, headers: Mapping[str, str]) -> PrivateAPIResponse:
        if headers.get("x-confirm-delete") != record_id:
            return self._response(409, {"error": "deletion_confirmation_required"})
        try:
            record = self.store.read(record_id)
            deleted = self.store.delete(record_id)
        except (FileNotFoundError, ValueError):
            deleted = False
        except (RuntimeError, KeyError, TypeError):
            return self._response(500, {"error": "record_unavailable"})
        if not deleted:
            return self._response(404, {"error": "not_found"})
        if record.get("still_image_path") and self.image_store is not None:
            try:
                self.image_store.delete(record_id)
            except RuntimeError:
                return self._response(500, {"error": "attachment_deletion_incomplete"})
        if self.speech_store is not None:
            self.speech_store.delete(record_id)
        return self._response(204, None)

    def _read_audio(self, record_id: str) -> PrivateAPIResponse:
        if self.speech_store is None:
            return self._response(404, {"error": "not_found"})
        try:
            self.store.read(record_id)
            audio = self.speech_store.read(record_id)
        except (FileNotFoundError, ValueError):
            return self._response(404, {"error": "not_found"})
        except (RuntimeError, KeyError, TypeError):
            return self._response(500, {"error": "audio_unavailable"})
        return PrivateAPIResponse(200, audio, {"Cache-Control": "no-store", "Content-Type": "audio/mpeg",
            "Content-Length": str(len(audio)), "Content-Disposition": 'inline; filename="creature-reply.mp3"',
            "X-Content-Type-Options": "nosniff"})

    def _read_image(self, record_id: str) -> PrivateAPIResponse:
        if self.image_store is None:
            return self._response(404, {"error": "not_found"})
        try:
            record = self.store.read(record_id)
            if not record.get("still_image_path"):
                return self._response(404, {"error": "not_found"})
            image = self.image_store.read(record_id)
        except (FileNotFoundError, ValueError):
            return self._response(404, {"error": "not_found"})
        except (RuntimeError, KeyError, TypeError):
            return self._response(500, {"error": "image_unavailable"})
        return PrivateAPIResponse(
            200,
            image.data,
            {
                "Cache-Control": "no-store",
                "Content-Type": image.media_type,
                "Content-Length": str(len(image.data)),
                "Content-Disposition": 'inline; filename="conversation-still"',
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; sandbox",
            },
        )

    @staticmethod
    def _safe_participant(participant: dict[str, Any]) -> dict[str, Any]:
        safe = dict(participant)
        embedding = safe.pop("facial_embedding", None)
        safe["facial_embedding_present"] = embedding is not None
        return safe

    @staticmethod
    def _response(status: int, body: dict[str, Any] | None) -> PrivateAPIResponse:
        return PrivateAPIResponse(status, body, {"Cache-Control": "no-store"})
