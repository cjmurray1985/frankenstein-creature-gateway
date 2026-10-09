from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audio import AlsaAdaptiveTurnAudioInput
from .config import RuntimeConfig
from .factory import build_audio_adapters, build_runtime
from .playback import AlsaPCMFilePlayer


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded live Creature turn")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="plughw:2,0")
    parser.add_argument("--max-duration", type=int, default=30)
    parser.add_argument("--end-silence-ms", type=int, default=1200)
    parser.add_argument("--gain", type=float, default=.75)
    args = parser.parse_args()
    config = RuntimeConfig.load(args.config)
    runtime = build_runtime(config, root=Path(__file__).resolve().parent.parent)
    detector, transcriber = build_audio_adapters(config)
    runtime.streaming_output = args.output
    audio = AlsaAdaptiveTurnAudioInput(args.capture, args.device, args.max_duration, args.end_silence_ms)
    turn = runtime.handle_audio(audio, detector, transcriber)
    if turn is None:
        print(json.dumps({"status": "no_speech_detected"})); return 2
    AlsaPCMFilePlayer(args.device, args.gain).play(args.output)
    print(json.dumps(turn.to_dict(), indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
