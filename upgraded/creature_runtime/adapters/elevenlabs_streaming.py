from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlencode

from ..models import Emotion, VocalContext
from .elevenlabs_cloud import _STREAM_FILTER


@dataclass(frozen=True)
class StreamingAudioTiming:
    first_network_audio_seconds: float | None
    first_processed_audio_seconds: float | None
    total_seconds: float
    network_audio_bytes: int
    processed_pcm_bytes: int


def decode_audio_frame(raw: str) -> tuple[bytes, bool]:
    message = json.loads(raw)
    if message.get("error"):
        raise RuntimeError(f"ElevenLabs streaming error: {message['error']}")
    encoded = message.get("audio")
    audio = base64.b64decode(encoded) if encoded else b""
    return audio, bool(message.get("is_final"))


def _next_or_sentinel(iterator, sentinel):
    try:
        return next(iterator)
    except StopIteration:
        return sentinel


def _write_pipe(stream, data: bytes) -> None:
    stream.write(data)
    stream.flush()


def ffmpeg_input_args(output_format: str) -> list[str]:
    if output_format.startswith("pcm_"):
        try:
            sample_rate = int(output_format.removeprefix("pcm_"))
        except ValueError as exc:
            raise ValueError(f"invalid PCM output format: {output_format}") from exc
        return ["-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0"]
    # The format is already known; do not buffer a large MP3 probe before decoding.
    return ["-probesize", "32", "-analyzeduration", "0", "-f", "mp3", "-i", "pipe:0"]


def streaming_performance_text(text: str, emotion: Emotion, context: VocalContext | None = None) -> str:
    # Long prose stage directions can trigger input_text_empty for short replies
    # on the dialogue WebSocket. Keep the emotional cues below its ~8-word
    # buffering threshold; the selected voice and DSP retain the vocal identity.
    tags = f"[weary] [{emotion.value}]"
    if context is not None and context.speaker_is_young:
        tags += " [gentle]"
    elif context is not None and context.crowd_mode:
        tags += " [projecting]"
    return f"{tags} {text.strip()}"


@dataclass(frozen=True)
class ElevenLabsDialogueStreamer:
    voice_id: str
    ffmpeg_executable: str = "ffmpeg"
    model_id: str = "eleven_v3_conversational"
    output_format: str = "mp3_44100_128"
    api_key_env: str = "ELEVENLABS_API_KEY"
    websocket_connect: Callable | None = None

    def stream_to_pcm(
        self,
        text_chunks: Iterable[str],
        emotion: Emotion,
        destination: Path,
        *,
        context: VocalContext | None = None,
        on_processed_chunk: Callable[[bytes], None] | None = None,
        flush_after_first_chunk: bool = False,
    ) -> StreamingAudioTiming:
        api_key = os.environ.get(self.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(f"required secret is not set: {self.api_key_env}")
        return asyncio.run(
            self._stream_to_pcm(
                text_chunks,
                emotion,
                destination,
                api_key,
                context=context,
                on_processed_chunk=on_processed_chunk,
                flush_after_first_chunk=flush_after_first_chunk,
            )
        )

    async def _stream_to_pcm(
        self,
        text_chunks: Iterable[str],
        emotion: Emotion,
        destination: Path,
        api_key: str,
        *,
        context: VocalContext | None,
        on_processed_chunk: Callable[[bytes], None] | None,
        flush_after_first_chunk: bool,
    ) -> StreamingAudioTiming:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError("install the optional 'streaming' dependency") from exc

        connect = self.websocket_connect or websockets.connect
        query = urlencode({"model_id": self.model_id, "output_format": self.output_format})
        uri = f"wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input?{query}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        first_network_at: float | None = None
        first_processed_at: float | None = None
        network_bytes = 0
        processed_bytes = 0
        timing_lock = threading.Lock()
        reader_error: list[BaseException] = []

        process = subprocess.Popen(
            [
                self.ffmpeg_executable,
                "-hide_banner",
                "-loglevel",
                "error",
                *ffmpeg_input_args(self.output_format),
                "-filter_complex",
                _STREAM_FILTER,
                "-map",
                "[out]",
                "-f",
                "s16le",
                "-ar",
                "44100",
                "-ac",
                "1",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert process.stdin is not None and process.stdout is not None

        def read_processed() -> None:
            nonlocal first_processed_at, processed_bytes
            try:
                with destination.open("wb") as output:
                    while True:
                        chunk = process.stdout.read(4096)
                        if not chunk:
                            break
                        with timing_lock:
                            if first_processed_at is None:
                                first_processed_at = time.monotonic()
                            processed_bytes += len(chunk)
                        output.write(chunk)
                        if on_processed_chunk is not None:
                            on_processed_chunk(chunk)
            except BaseException as exc:
                reader_error.append(exc)

        reader = threading.Thread(target=read_processed, name="creature-ffmpeg-reader", daemon=True)
        reader.start()
        iterator = iter(text_chunks)
        sentinel = object()

        try:
            async with connect(uri) as websocket:
                await websocket.send(json.dumps({"voices": [self.voice_id], "xi_api_key": api_key}))

                async def send_text() -> None:
                    first = True
                    while True:
                        chunk = await asyncio.to_thread(_next_or_sentinel, iterator, sentinel)
                        if chunk is sentinel:
                            break
                        text = str(chunk).strip()
                        if not text:
                            continue
                        is_first = first
                        if is_first:
                            text = streaming_performance_text(text, emotion, context)
                            first = False
                        await websocket.send(
                            json.dumps(
                                {
                                    "inputs": [
                                        {"text": text + " ", "voice_id": self.voice_id, "new_turn": False}
                                    ]
                                }
                            )
                        )
                        if is_first and flush_after_first_chunk:
                            await websocket.send(json.dumps({"flush": True}))
                    await websocket.send(json.dumps({"close_socket": True}))

                async def receive_audio() -> None:
                    nonlocal first_network_at, network_bytes
                    while True:
                        raw = await websocket.recv()
                        audio, final = decode_audio_frame(raw)
                        if audio:
                            if reader_error:
                                raise RuntimeError("processed-audio consumer failed") from reader_error[0]
                            now = time.monotonic()
                            if first_network_at is None:
                                first_network_at = now
                            network_bytes += len(audio)
                            await asyncio.to_thread(_write_pipe, process.stdin, audio)
                        if final:
                            return

                await asyncio.wait_for(
                    asyncio.gather(send_text(), receive_audio()),
                    timeout=30,
                )
        finally:
            # A provider rejection often leaves FFmpeg with no input. Do not
            # replace that actionable error with the resulting decoder exit.
            upstream_error = sys.exc_info()[1]
            pipe_error = None
            try:
                process.stdin.close()
            except BrokenPipeError as exc:
                pipe_error = exc
            try:
                await asyncio.to_thread(process.wait, 10)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, 2)
            reader.join(timeout=30)
            if reader.is_alive():
                process.kill()
                raise RuntimeError("streaming audio processor did not finish")
            if reader_error and upstream_error is None:
                raise RuntimeError("processed-audio consumer failed") from reader_error[0]
            if process.returncode != 0 and upstream_error is None:
                raise RuntimeError(f"streaming audio processor exited {process.returncode}")
            if pipe_error is not None and upstream_error is None:
                raise RuntimeError("streaming audio input pipe closed") from pipe_error

        completed = time.monotonic()
        return StreamingAudioTiming(
            None if first_network_at is None else first_network_at - started,
            None if first_processed_at is None else first_processed_at - started,
            completed - started,
            network_bytes,
            processed_bytes,
        )
