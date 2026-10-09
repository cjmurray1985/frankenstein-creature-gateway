from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Mapping
from urllib.parse import parse_qs, urlsplit

from .dashboard import DASHBOARD_CSS, render_dashboard, render_record
from .private_api import PrivateConversationAPI


@dataclass(frozen=True)
class DashboardResponse:
    status: int
    body: bytes
    headers: dict[str, str]


@dataclass(frozen=True)
class DashboardApplication:
    api: PrivateConversationAPI

    def handle(self, method: str, target: str, headers: Mapping[str, str], body: bytes = b"") -> DashboardResponse:
        path = urlsplit(target).path
        if path == "/assets/dashboard.css" and method == "GET":
            response = self.api.handle("GET", "/records", headers)
            if response.status != 200:
                return self._error(response.status)
            css = DASHBOARD_CSS.encode("utf-8")
            return DashboardResponse(200, css, {
                "Content-Type": "text/css; charset=utf-8", "Content-Length": str(len(css)),
                "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            })
        if path == "/" and method == "GET":
            response = self.api.handle("GET", "/records", headers)
            if response.status != 200 or not isinstance(response.body, dict):
                return self._error(response.status)
            page = render_dashboard(response.body["records"])
            return self._html(200, page)
        if path.startswith("/records/") and path.endswith("/delete") and method == "POST":
            record_id = path.removeprefix("/records/").removesuffix("/delete")
            if len(body) > 4096:
                return self._error(413)
            if not body:
                return self._error(409)
            try:
                confirmation = parse_qs(body.decode("utf-8"), strict_parsing=True).get("confirm", [""])[0]
            except (UnicodeDecodeError, ValueError):
                return self._error(400)
            if confirmation != record_id:
                return self._error(409)
            deletion_headers = dict(headers)
            deletion_headers["X-Confirm-Delete"] = record_id
            response = self.api.handle("DELETE", f"/records/{record_id}", deletion_headers)
            if response.status == 204:
                return DashboardResponse(303, b"", {"Location": "/", "Cache-Control": "no-store"})
            return self._error(response.status)
        if path.startswith("/records/") and path.endswith("/image") and method == "GET":
            response = self.api.handle("GET", path, headers)
            if response.status == 200 and isinstance(response.body, bytes):
                return DashboardResponse(200, response.body, response.headers or {})
            return self._error(response.status)
        if path.startswith("/records/") and path.endswith("/audio") and method == "GET":
            response = self.api.handle("GET", path, headers)
            if response.status == 200 and isinstance(response.body, bytes):
                return DashboardResponse(200, response.body, response.headers or {})
            return self._error(response.status)
        if path.startswith("/records/") and path.count("/") == 2 and method == "GET":
            response = self.api.handle("GET", path, headers)
            if response.status != 200 or not isinstance(response.body, dict):
                return self._error(response.status)
            return self._html(200, render_record(response.body["record"]))
        return self._error(404)

    @staticmethod
    def _html(status: int, page: str) -> DashboardResponse:
        body = page.encode("utf-8")
        return DashboardResponse(status, body, {
            "Content-Type": "text/html; charset=utf-8", "Content-Length": str(len(body)),
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "Referrer-Policy": "no-referrer",
        })

    @staticmethod
    def _error(status: int) -> DashboardResponse:
        body = json.dumps({"error": "unavailable"}).encode("utf-8")
        return DashboardResponse(status, body, {"Content-Type": "application/json", "Cache-Control": "no-store"})


def create_loopback_server(host: str, port: int, app: DashboardApplication) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("private dashboard must bind to loopback")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self): self._serve("GET")
        def do_POST(self): self._serve("POST")
        def _serve(self, method: str):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                response = app._error(413)
            else:
                response = app.handle(method, self.path, dict(self.headers.items()), self.rfile.read(length))
            self.send_response(response.status)
            for key, value in response.headers.items(): self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.body)
        def log_message(self, _format, *_args): return

    return ThreadingHTTPServer((host, port), Handler)
