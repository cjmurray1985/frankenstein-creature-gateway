from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import RuntimeConfig
from .factory import build_runtime
from .records import EncryptedConversationStore, ParticipantRecord
from .session import ConversationSessionController
from .session_runner import CreatureSessionRunner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run an offline, hardware-safe, encrypted multi-turn Creature session"
    )
    result.add_argument("--config", type=Path, default=Path("config/creature-runtime.json"))
    result.add_argument("--record-dir", type=Path, required=True)
    result.add_argument("--key-env", default="CREATURE_RECORD_KEY")
    result.add_argument("--speaker-id", default="visitor-1")
    result.add_argument("--speaker-label", default="my friend")
    result.add_argument("--text", action="append", required=True, help="repeat for each visitor turn")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = RuntimeConfig.load(config_path)
    runtime = build_runtime(config, root=root)
    participant = ParticipantRecord(args.speaker_id, args.speaker_label)
    store = EncryptedConversationStore(args.record_dir, key_env=args.key_env)
    lifecycle = ConversationSessionController(store, (participant,))
    runner = CreatureSessionRunner(runtime, lifecycle)

    turns = [runner.handle_text(text, args.speaker_id).to_dict() for text in args.text]
    record = lifecycle.end()
    if record is None:
        raise RuntimeError("session ended without a completed turn")
    print(
        json.dumps(
            {
                "turns": turns,
                "archive": {
                    "record_id": record.record_id,
                    "started_at": record.started_at,
                    "ended_at": record.ended_at,
                    "turn_count": len(record.turns),
                    "emotional_summary": record.emotional_summary,
                    "encrypted": True,
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

