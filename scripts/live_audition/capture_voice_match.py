#!/usr/bin/env python3
"""Capture a bounded, explicitly authorized GPT-Live/ElevenLabs voice-match pair."""
from __future__ import annotations

import argparse
from array import array
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import wave

from websockets.sync.client import connect

from creature_runtime.adapters.elevenlabs_streaming import ElevenLabsDialogueStreamer
from creature_runtime.models import Emotion


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "analysis/audio/voice-match-2026-09-26"
DEFAULT_TEXT = (
    "Before you judge me by this ruined form, understand that I was not born cruel."
)
VOICE_ID = "EDBh1NBfgpE9Lo2jrcIH"


def secret(environment: str, keychain_service: str) -> str:
    value = os.environ.get(environment, "").strip()
    if value:
        return value
    return subprocess.run(
        ["security", "find-generic-password", "-s", keychain_service, "-w"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def write_pcm16_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    if len(pcm) % 2:
        raise ValueError("PCM16 byte count must be even")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def capture_live(path: Path, transcript_path: Path, text: str, api_key: str) -> dict:
    audio = bytearray()
    transcript = []
    started_audio = False
    last_audio = None
    started_at = time.monotonic()
    closed_usage = None
    event_counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="creature-voice-match-") as temporary:
        spoken_prompt = Path(temporary) / "prompt.aiff"
        subprocess.run([
            "/usr/bin/say", "-v", "Alex", "-o", str(spoken_prompt),
            "Please repeat this sentence exactly, once. " + text,
        ], check=True, timeout=20)
        prompt_pcm = subprocess.run([
            shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg",
            "-hide_banner", "-loglevel", "error", "-i", str(spoken_prompt),
            "-f", "s16le", "-ar", "24000", "-ac", "1", "pipe:1",
        ], check=True, capture_output=True, timeout=20).stdout
    instruction = (
        "You are the Creature from Mary Shelley's Frankenstein. Use Meridian's lowest "
        "comfortable register. Your immense damaged body makes speech costly. Speak very "
        "slowly in short breath-groups, with one restrained inhale before beginning and a "
        "brief recovery pause at the comma. Remain lucid and intelligible; do not pant or "
        "growl. When instructed, speak the supplied calibration sentence exactly once, "
        "without introduction or commentary, then remain silent."
    )
    with connect(
        "wss://api.openai.com/v1/live/sessions",
        additional_headers={"Authorization": "Bearer " + api_key},
        open_timeout=20,
        max_size=8_000_000,
    ) as socket:
        socket.send(json.dumps({
            "type": "session.start",
            "event_id": "voice_match_start",
            "session": {
                "model": "gpt-live-1",
                "instructions": instruction,
                "audio": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "output": {"voice": "meridian"},
                },
                "store": False,
                "delegation": {"type": "client"},
            },
        }))
        instructed = False
        session_started = False
        last_silence_sent = 0.0
        prompt_offset = 0
        closing = False
        close_deadline = None
        while True:
            now = time.monotonic()
            if session_started and not closing and now - last_silence_sent >= .1:
                # GPT-Live expects the primary audio stream to remain active while
                # an instructions.append request initiates speech.
                chunk = prompt_pcm[prompt_offset:prompt_offset + 4800]
                prompt_offset += len(chunk)
                if not chunk:
                    chunk = bytes(2400 * 2)
                socket.send(json.dumps({
                    "type": "session.input_audio.append",
                    "audio": base64.b64encode(chunk).decode(),
                }))
                last_silence_sent = now
            if started_audio and last_audio and not closing and time.monotonic() - last_audio > 2.5:
                socket.send(json.dumps({"type": "session.close", "event_id": "voice_match_close"}))
                closing = True
                close_deadline = time.monotonic() + 15
            if time.monotonic() - started_at > 45 or (close_deadline and time.monotonic() > close_deadline):
                raise TimeoutError(
                    "GPT-Live calibration capture did not finalize; "
                    f"events={event_counts}, input_bytes={prompt_offset}/{len(prompt_pcm)}"
                )
            try:
                event = json.loads(socket.recv(timeout=0.05))
            except TimeoutError:
                continue
            kind = event.get("type")
            event_counts[kind] = event_counts.get(kind, 0) + 1
            if kind == "session.started" and not instructed:
                session_started = True
                socket.send(json.dumps({
                    "type": "session.instructions.append",
                    "event_id": "voice_match_line",
                    "delegation_id": None,
                    "content": (
                        "The next spoken request is a bounded voice calibration. Follow its "
                        "request for exact wording, speak once, then remain silent."
                    ),
                }))
                instructed = True
            elif kind == "session.output_audio.delta":
                chunk = base64.b64decode(event.get("delta", ""))
                if chunk:
                    audio.extend(chunk)
                    levels = array("h")
                    levels.frombytes(chunk)
                    if levels and max(abs(value) for value in levels) >= 160:
                        started_audio = True
                        last_audio = time.monotonic()
            elif kind == "session.output_transcript.delta":
                transcript.append(event.get("delta", ""))
            elif kind == "error":
                raise RuntimeError(event.get("error", {}).get("message", "GPT-Live capture failed"))
            elif kind == "session.closed":
                closed_usage = event.get("usage")
                break
    if not audio:
        raise RuntimeError("GPT-Live returned no calibration audio")
    write_pcm16_wav(path, bytes(audio), 24000)
    spoken = "".join(transcript).strip()
    transcript_path.write_text(spoken + "\n")
    return {"transcript": spoken, "pcm_bytes": len(audio), "usage": closed_usage}


def capture_elevenlabs(path: Path, text: str, api_key: str) -> dict:
    os.environ["ELEVENLABS_API_KEY"] = api_key
    pcm_path = path.with_suffix(".pcm")
    streamer = ElevenLabsDialogueStreamer(
        voice_id=VOICE_ID,
        ffmpeg_executable=shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg",
    )
    timing = streamer.stream_to_pcm(
        [text], Emotion.CURIOUS, pcm_path, flush_after_first_chunk=True,
    )
    pcm = pcm_path.read_bytes()
    write_pcm16_wav(path, pcm, 44100)
    return {
        "pcm_bytes": len(pcm),
        "first_network_audio_seconds": timing.first_network_audio_seconds,
        "first_processed_audio_seconds": timing.first_processed_audio_seconds,
        "total_seconds": timing.total_seconds,
    }


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    live_path = args.output / "gpt-live-meridian-raw.wav"
    eleven_path = args.output / "elevenlabs-mourning-colossus.wav"
    manifest = {
        "purpose": "bounded same-line voice matching; user explicitly authorized local recordings",
        "text": args.text,
        "gpt_live": capture_live(
            live_path, args.output / "gpt-live-transcript.txt", args.text,
            secret("OPENAI_API_KEY", "frankenstein-openai"),
        ),
        "elevenlabs": capture_elevenlabs(
            eleven_path, args.text,
            secret("ELEVENLABS_API_KEY", "frankenstein-elevenlabs"),
        ),
    }
    manifest["gpt_live"]["file"] = live_path.name
    manifest["gpt_live"]["duration_seconds"] = duration(live_path)
    manifest["elevenlabs"]["file"] = eleven_path.name
    manifest["elevenlabs"]["duration_seconds"] = duration(eleven_path)
    (args.output / "capture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
