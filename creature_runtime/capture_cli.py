from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .adapters.local import WhisperCppTranscriber
from .audio import AlsaOneTurnAudioInput, WaveEnergyTurnDetector


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture and transcribe one bounded ReSpeaker turn")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="plughw:2,0")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--whisper", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    path = AlsaOneTurnAudioInput(args.output, args.device, args.duration).capture()
    turn = WaveEnergyTurnDetector().detect(path)
    if turn is None:
        print(json.dumps({"status": "no_speech_detected", "recording": str(path)}))
        return 2
    transcript = WhisperCppTranscriber(args.whisper, args.model).transcribe(turn)
    print(json.dumps({"status": "transcribed", "transcript": transcript,
                      "speech_start_seconds": turn.started_seconds,
                      "speech_end_seconds": turn.ended_seconds,
                      "recording": str(path)}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
