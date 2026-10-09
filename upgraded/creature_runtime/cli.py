from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .audio import PrerecordedAudioInput
from .config import RuntimeConfig
from .factory import build_audio_adapters, build_runtime


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run one hardware-safe Creature conversation turn")
    result.add_argument("--config", type=Path, default=Path("config/creature-runtime.json"))
    result.add_argument(
        "--output",
        type=Path,
        help="override the streaming PCM output path for this turn",
    )
    visitor = result.add_mutually_exclusive_group(required=True)
    visitor.add_argument("--text", help="visitor text supplied in place of speech")
    visitor.add_argument("--audio", type=Path, help="prerecorded visitor audio")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = RuntimeConfig.load(config_path)
    if args.output is not None:
        config = replace(config, streaming_output=str(args.output))
    runtime = build_runtime(config, root=root)
    if args.text is not None:
        turn = runtime.handle_text(args.text)
    else:
        detector, transcriber = build_audio_adapters(config)
        turn = runtime.handle_audio(PrerecordedAudioInput(args.audio), detector, transcriber)
        if turn is None:
            print(json.dumps({"status": "no_speech_detected"}, indent=2))
            return 2
    print(json.dumps(turn.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
