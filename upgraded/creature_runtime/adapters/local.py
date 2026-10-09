from __future__ import annotations

import subprocess
from dataclasses import dataclass

from ..models import AudioTurn


@dataclass(frozen=True)
class StaticTranscriber:
    text: str

    def transcribe(self, audio: AudioTurn) -> str:
        return self.text.strip()


@dataclass(frozen=True)
class WhisperCppTranscriber:
    executable: str
    model: str

    def transcribe(self, audio: AudioTurn) -> str:
        command = [self.executable, "-m", self.model, "-f", str(audio.path), "-nt"]
        if audio.started_seconds > 0:
            command.extend(["-ot", str(round(audio.started_seconds * 1000))])
        if audio.ended_seconds is not None:
            duration = max(1, round((audio.ended_seconds - audio.started_seconds) * 1000))
            command.extend(["-d", str(duration)])
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        text = result.stdout.strip()
        if not text:
            raise RuntimeError("whisper.cpp returned an empty transcript")
        return text
