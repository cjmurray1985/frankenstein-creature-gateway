from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeConfig:
    dry_run: bool = True
    responder: str = "local"
    tts: str = "request_only"
    motion: str = "request_only"
    voice: str = "creature-local-placeholder"
    history_turns: int = 8
    turn_detector: str = "wave_energy"
    transcriber: str = "mock"
    mock_transcript: str = ""
    whisper_executable: str = ""
    whisper_model: str = ""
    provisional_whisper_model: str = ""
    tts_output: str = "analysis/audio/creature-reply.mp3"
    tts_model: str = "eleven_v3"
    tts_api_key_env: str = "ELEVENLABS_API_KEY"
    ffmpeg_executable: str = "ffmpeg"
    latency_masking: bool = False
    cue_directory: str = "assets/audio/latency"
    acknowledgment_delay_seconds: float = 3.0
    post_acknowledgment_pause_seconds: float = 2.0
    playback: str = "none"
    playback_executable: str = "ffplay"
    playback_device: str = "plughw:2,0"
    mock_audience_count: int = 1
    mock_speaker_is_young: bool = False
    streaming_response: bool = False
    streaming_output: str = "analysis/audio/creature-stream.pcm"

    @classmethod
    def load(cls, path: Path) -> "RuntimeConfig":
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
        config = cls(**data)
        if config.motion != "request_only":
            raise ValueError("only the hardware-free request_only motion adapter is supported")
        if config.history_turns < 1:
            raise ValueError("history_turns must be positive")
        if config.turn_detector not in {"wave_energy", "whole_file"}:
            raise ValueError(f"unsupported turn detector: {config.turn_detector}")
        if config.transcriber not in {"mock", "whisper_cpp", "openai"}:
            raise ValueError(f"unsupported transcriber: {config.transcriber}")
        if config.transcriber == "whisper_cpp" and not (
            config.whisper_executable and config.whisper_model
        ):
            raise ValueError("whisper_cpp requires whisper_executable and whisper_model")
        if config.tts == "elevenlabs" and not config.voice.strip():
            raise ValueError("elevenlabs TTS requires a voice id")
        if config.acknowledgment_delay_seconds < 0:
            raise ValueError("acknowledgment_delay_seconds must not be negative")
        if config.post_acknowledgment_pause_seconds < 0:
            raise ValueError("post_acknowledgment_pause_seconds must not be negative")
        if config.playback not in {"none", "ffplay", "alsa"}:
            raise ValueError(f"unsupported playback adapter: {config.playback}")
        if not config.playback_device or any(character.isspace() for character in config.playback_device):
            raise ValueError("playback_device must be a non-empty ALSA token")
        if config.mock_audience_count < 1:
            raise ValueError("mock_audience_count must be positive")
        if config.streaming_response and not (
            config.responder == "openai" and config.tts == "elevenlabs"
        ):
            raise ValueError("streaming_response requires openai responder and elevenlabs TTS")
        return config
