from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from .audit import EncryptedAuditLog
from .dashboard_http import DashboardApplication, create_loopback_server
from .images import EncryptedStillImageStore
from .private_api import PrivateConversationAPI, TailscaleServeAuthenticator
from .records import EncryptedConversationStore
from .speech_archive import EncryptedSpeechStore


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run the private Creature Archive on loopback")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=8765)
    result.add_argument("--data-root", type=Path, default=Path("/var/lib/frankenstein/creature-dashboard"))
    result.add_argument("--owner-env", default="CREATURE_DASHBOARD_OWNER")
    result.add_argument("--key-env", default="CREATURE_RECORD_KEY")
    return result


def build_application(data_root: Path, owner: str, key_env: str) -> DashboardApplication:
    records = EncryptedConversationStore(data_root / "records", key_env=key_env)
    images = EncryptedStillImageStore(data_root / "images", key_env=key_env)
    speech = EncryptedSpeechStore(data_root / "speech", key_env=key_env)
    audit = EncryptedAuditLog(data_root / "audit", key_env=key_env)
    api = PrivateConversationAPI(
        records,
        image_store=images,
        speech_store=speech,
        authenticator=TailscaleServeAuthenticator(owner),
        audit_log=audit,
    )
    return DashboardApplication(api)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    owner = os.environ.get(args.owner_env, "").strip()
    if not owner:
        raise RuntimeError(f"required dashboard owner is not set: {args.owner_env}")
    app = build_application(args.data_root, owner, args.key_env)
    server = create_loopback_server(args.host, args.port, app)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
