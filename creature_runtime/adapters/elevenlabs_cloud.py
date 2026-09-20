from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..models import Emotion, SpeechRequest, VocalContext


ApiKeyProvider = Callable[[str], str]
HttpPost = Callable[[str, dict[str, object], str], bytes]
AudioProcessor = Callable[[Path, Path, str], None]


_DIRECTION = {
    Emotion.DORMANT: "barely awake, profoundly low, weary",
    Emotion.CURIOUS: "profoundly low, watchful, quietly curious",
    Emotion.HOPEFUL: "profoundly low, weary, cautiously hopeful",
    Emotion.ENGAGED: "profoundly low, intent, stirred by fellowship",
    Emotion.WARY: "profoundly low, guarded, measuring every word",
    Emotion.HURT: "profoundly low, wounded, struggling to remain composed",
    Emotion.ANGRY: "profoundly low, controlled anger beneath every word",
    Emotion.WITHDRAWN: "profoundly low, exhausted, retreating into grief",
}

_FILTER = (
    "[0:a]asplit=3[dry][main][sub];"
    "[dry]volume=0.07[d];"
    "[main]asetrate=31183,aresample=44100,atempo=1.4142,"
    "highpass=f=32,lowpass=f=10200,volume=0.94[m];"
    "[sub]asetrate=22050,aresample=44100,atempo=2.0,"
    "lowpass=f=2100,highpass=f=28,volume=0.10[s];"
    "[d][m][s]amix=inputs=3:normalize=0,"
    "acompressor=threshold=0.12:ratio=2.0:attack=20:release=240,"
    "loudnorm=I=-19:TP=-2:LRA=10[out]"
)

# The mastered-file filter above may buffer roughly a second in loudnorm.
# Streaming retains the selected identity layers but uses a look-ahead limiter
# so processed PCM can be released as chunks arrive.
_STREAM_FILTER = (
    "[0:a]asplit=3[dry][main][sub];"
    "[dry]volume=0.07[d];"
    "[main]asetrate=31183,aresample=44100,atempo=1.4142,"
    "highpass=f=32,lowpass=f=10200,volume=0.94[m];"
    "[sub]asetrate=22050,aresample=44100,atempo=2.0,"
    "lowpass=f=2100,highpass=f=28,volume=0.10[s];"
    "[d][m][s]amix=inputs=3:normalize=0,"
    "acompressor=threshold=0.12:ratio=2.0:attack=20:release=240,"
    "volume=2.2,"
    "alimiter=limit=0.794:attack=5:release=100:level=false[out]"
)


def _environment_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required secret is not set: {name}")
    return value


def _post_json(url: str, payload: dict[str, object], api_key: str) -> bytes:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "xi-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _mourning_colossus_process(source: Path, destination: Path, ffmpeg: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-filter_complex",
            _FILTER,
            "-map",
            "[out]",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-b:a",
            "192k",
            str(destination),
        ],
        check=True,
        timeout=30,
    )


def performance_text(text: str, emotion: Emotion, context: VocalContext | None = None) -> str:
    direction = _DIRECTION[emotion]
    if context is not None and context.speaker_is_young:
        direction += ", gentle and patient, with softened pacing for a young friend"
    elif context is not None and context.crowd_mode:
        direction += ", projecting with room-filling authority while keeping the same breath"
    breath = "a constricted breath drags through a failing chest"
    if emotion in {Emotion.HURT, Emotion.WITHDRAWN}:
        breath = "a constricted breath trembles through a failing chest"
    elif emotion is Emotion.ANGRY:
        breath = "a harsh, constricted breath drags through a failing chest"
    return f"[{direction}] [{breath}] {text.strip()}"


@dataclass(frozen=True)
class ElevenLabsMourningColossusTTS:
    voice_id: str
    output_path: Path
    model_id: str = "eleven_v3"
    api_key_env: str = "ELEVENLABS_API_KEY"
    ffmpeg_executable: str = "ffmpeg"
    api_key_provider: ApiKeyProvider = _environment_secret
    http_post: HttpPost = _post_json
    audio_processor: AudioProcessor = _mourning_colossus_process

    def request(
        self, text: str, emotion: Emotion, *, dry_run: bool, context: VocalContext | None = None
    ) -> SpeechRequest:
        if dry_run:
            return SpeechRequest(
                text, type(self).__name__, "mourning-colossus", True, str(self.output_path)
            )

        api_key = self.api_key_provider(self.api_key_env)
        raw_path = self.output_path.with_name(f"{self.output_path.stem}-raw.mp3")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "text": performance_text(text, emotion, context),
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.34,
                "use_speaker_boost": True,
                "speed": 0.9,
            },
        }
        audio = self.http_post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            "?output_format=mp3_44100_128",
            payload,
            api_key,
        )
        raw_path.write_bytes(audio)
        self.audio_processor(raw_path, self.output_path, self.ffmpeg_executable)
        return SpeechRequest(
            text, type(self).__name__, "mourning-colossus", False, str(self.output_path)
        )
