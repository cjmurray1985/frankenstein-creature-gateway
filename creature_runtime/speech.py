from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Emotion, SpeechRequest, VocalContext


@dataclass(frozen=True)
class RequestOnlyTTS:
    voice: str = "creature-local-placeholder"

    def request(
        self, text: str, emotion: Emotion, *, dry_run: bool, context: VocalContext | None = None
    ) -> SpeechRequest:
        return SpeechRequest(text, type(self).__name__, self.voice, dry_run)


@dataclass(frozen=True)
class PiperTTS:
    executable: str
    model: Path
    output_path: Path
    voice: str = "piper"

    def request(
        self, text: str, emotion: Emotion, *, dry_run: bool, context: VocalContext | None = None
    ) -> SpeechRequest:
        if dry_run:
            return SpeechRequest(text, type(self).__name__, self.voice, True, str(self.output_path))
        import subprocess

        subprocess.run(
            [self.executable, "--model", str(self.model), "--output_file", str(self.output_path)],
            input=text,
            text=True,
            check=True,
            timeout=30,
        )
        return SpeechRequest(text, type(self).__name__, self.voice, False, str(self.output_path))
