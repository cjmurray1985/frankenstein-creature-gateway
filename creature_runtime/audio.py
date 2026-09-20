from __future__ import annotations

import math
import array
import os
import subprocess
import wave
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .models import AudioTurn
from .endpointing import EndpointController, EndpointDecision, EndpointEvent, PartialTranscript


def pcm_rms(chunk: bytes, sample_width: int, channels: int) -> int:
    if sample_width not in {1, 2, 4}:
        raise ValueError(f"unsupported PCM sample width: {sample_width}")
    frame_width = sample_width * channels
    if not chunk or len(chunk) % frame_width:
        return 0
    squared = 0.0
    frame_count = len(chunk) // frame_width
    for frame_start in range(0, len(chunk), frame_width):
        channel_total = 0
        for channel in range(channels):
            start = frame_start + channel * sample_width
            sample_bytes = chunk[start : start + sample_width]
            if sample_width == 1:
                sample = sample_bytes[0] - 128
            else:
                sample = int.from_bytes(sample_bytes, "little", signed=True)
            channel_total += sample
        mono = channel_total / channels
        squared += mono * mono
    return int(math.sqrt(squared / frame_count))


def terminal_pitch_direction(data: bytes, *, rate: int = 16000) -> str:
    """Conservative, dependency-free terminal pitch estimate for endpointing."""
    samples = array.array("h")
    samples.frombytes(data)
    frame = rate * 40 // 1000
    hop = rate * 20 // 1000
    active: list[int] = []
    for start in range(0, max(0, len(samples) - frame + 1), hop):
        window = samples[start:start + frame]
        rms = math.sqrt(sum(value * value for value in window) / len(window))
        if rms >= 500:
            active.append(start)
    if not active:
        return "unknown"
    end = active[-1] + frame
    pitches: list[float] = []
    for offset in range(max(0, end - rate // 2), max(0, end - frame + 1), hop):
        raw = samples[offset:offset + frame]
        rms = math.sqrt(sum(value * value for value in raw) / len(raw))
        if rms < 500:
            continue
        mean = sum(raw) / len(raw)
        centered = [value - mean for value in raw]
        best_lag, best_score = 0, 0.0
        for lag in range(rate // 350, rate // 65 + 1):
            left, right = centered[:-lag], centered[lag:]
            numerator = sum(a * b for a, b in zip(left, right))
            denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
            score = numerator / denominator if denominator else 0.0
            if score > best_score:
                best_lag, best_score = lag, score
        if best_lag and best_score >= 0.60:
            pitches.append(rate / best_lag)
    if len(pitches) < 6:
        return "unknown"
    third = max(2, len(pitches) // 3)
    first_values = sorted(pitches[:third])
    last_values = sorted(pitches[-third:])
    ratio = last_values[len(last_values) // 2] / first_values[len(first_values) // 2]
    if ratio >= 1.015:
        return "rising"
    if ratio <= 0.96:
        return "falling"
    return "level"


@dataclass(frozen=True)
class PrerecordedAudioInput:
    path: Path

    def capture(self) -> Path:
        if not self.path.is_file():
            raise FileNotFoundError(f"prerecorded audio not found: {self.path}")
        return self.path


@dataclass(frozen=True)
class AlsaOneTurnAudioInput:
    """Bounded ALSA capture with no playback or hardware-control capability."""

    destination: Path
    device: str = "plughw:2,0"
    duration_seconds: int = 10
    executable: str = "arecord"

    def __post_init__(self) -> None:
        if not 1 <= self.duration_seconds <= 30:
            raise ValueError("capture duration must be between 1 and 30 seconds")
        if not self.device or any(character.isspace() for character in self.device):
            raise ValueError("ALSA device must be a non-empty token")

    def capture(self) -> Path:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [self.executable, "-q", "-D", self.device, "-f", "S16_LE", "-r", "16000",
             "-c", "1", "-d", str(self.duration_seconds), str(self.destination)],
            check=True,
            timeout=self.duration_seconds + 10,
        )
        if not self.destination.is_file():
            raise RuntimeError("ALSA capture did not create a recording")
        return self.destination


@dataclass(frozen=True)
class AlsaAdaptiveTurnAudioInput:
    """Capture until trailing silence after speech, bounded by a safety ceiling."""

    destination: Path
    device: str = "plughw:2,0"
    max_duration_seconds: int = 30
    end_silence_ms: int = 1200
    threshold: int = 250
    frame_ms: int = 30
    executable: str = "arecord"
    process_factory: Callable = field(default=subprocess.Popen, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_duration_seconds <= 30:
            raise ValueError("maximum capture duration must be between 1 and 30 seconds")
        if self.end_silence_ms < 300 or self.end_silence_ms > 5000:
            raise ValueError("end silence must be between 300 and 5000 milliseconds")
        if not self.device or any(character.isspace() for character in self.device):
            raise ValueError("ALSA device must be a non-empty token")

    def capture(self) -> Path:
        rate, width, channels = 16000, 2, 1
        frames_per_chunk = rate * self.frame_ms // 1000
        chunk_bytes = frames_per_chunk * width * channels
        maximum_chunks = self.max_duration_seconds * 1000 // self.frame_ms
        silence_chunks = max(1, self.end_silence_ms // self.frame_ms)
        process = self.process_factory(
            [self.executable, "-q", "-D", self.device, "-t", "raw", "-f", "S16_LE", "-r", str(rate), "-c", str(channels)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        if process.stdout is None:
            raise RuntimeError("ALSA capture stdout is unavailable")
        captured: list[bytes] = []
        speech_started = False
        trailing_silence = 0
        try:
            for _ in range(maximum_chunks):
                chunk = process.stdout.read(chunk_bytes)
                if not chunk: break
                captured.append(chunk)
                active = pcm_rms(chunk, width, channels) >= self.threshold
                if active:
                    speech_started, trailing_silence = True, 0
                elif speech_started:
                    trailing_silence += 1
                    if trailing_silence >= silence_chunks: break
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=1)
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(self.destination), "wb") as output:
            output.setnchannels(channels); output.setsampwidth(width); output.setframerate(rate)
            output.writeframes(b"".join(captured))
        return self.destination


@dataclass
class AlsaSemanticTurnAudioInput:
    """Continuous ALSA capture with asynchronous provisional semantic endpointing."""

    destination: Path
    provisional_transcriber: Callable[[Path], str]
    device: str = "plughw:2,0"
    max_duration_seconds: int = 30
    threshold: int = 250
    frame_ms: int = 30
    executable: str = "arecord"
    process_factory: Callable = field(default=subprocess.Popen, repr=False, compare=False)
    controller_factory: Callable[[], EndpointController] = field(
        default=EndpointController, repr=False, compare=False
    )
    provisional_transcript: str | None = field(default=None, init=False)
    endpoint_events: list[EndpointDecision] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_duration_seconds <= 30:
            raise ValueError("maximum capture duration must be between 1 and 30 seconds")
        if not self.device or any(character.isspace() for character in self.device):
            raise ValueError("ALSA device must be a non-empty token")

    @staticmethod
    def _write_wave(path: Path, frames: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
            output.writeframes(frames)
        os.chmod(path, 0o600)

    def capture(self) -> Path:
        rate, width, channels = 16000, 2, 1
        chunk_bytes = rate * self.frame_ms // 1000 * width
        maximum_chunks = self.max_duration_seconds * 1000 // self.frame_ms
        process = self.process_factory(
            [self.executable, "-q", "-D", self.device, "-t", "raw", "-f", "S16_LE",
             "-r", str(rate), "-c", str(channels)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        if process.stdout is None:
            raise RuntimeError("ALSA capture stdout is unavailable")
        controller = self.controller_factory()
        frames: list[bytes] = []
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="endpoint-probe")
        future: Future[str] | None = None
        future_generation = -1
        future_snapshot: Path | None = None
        probe_number = 0
        snapshots: list[Path] = []
        committed = False
        self.provisional_transcript = None
        self.endpoint_events = []
        try:
            for index in range(maximum_chunks):
                chunk = process.stdout.read(chunk_bytes)
                if not chunk:
                    break
                frames.append(chunk)
                active = pcm_rms(chunk, width, channels) >= self.threshold
                events = controller.observe(active=active, at_ms=index * self.frame_ms)
                self.endpoint_events.extend(events)
                if any(event.event is EndpointEvent.TENTATIVE_END for event in events) and future is None:
                    snapshot = self.destination.with_name(f"{self.destination.stem}.probe-{probe_number}.wav")
                    probe_number += 1; snapshots.append(snapshot)
                    self._write_wave(snapshot, b"".join(frames))
                    future_generation = controller.generation
                    future_snapshot = snapshot
                    future = executor.submit(self.provisional_transcriber, snapshot)
                if future is not None and future.done():
                    try:
                        text = future.result().strip()
                    except Exception:
                        text = ""
                    generation_matches = future_generation == controller.generation
                    future = None
                    if generation_matches and text:
                        # Batch Whisper returns a final hypothesis for this
                        # immutable snapshot. Speech resumption is guarded by
                        # the generation token rather than a duplicate probe.
                        prosody = "unknown"
                        if future_snapshot is not None:
                            with wave.open(str(future_snapshot), "rb") as probe:
                                prosody = terminal_pitch_direction(
                                    probe.readframes(probe.getnframes()), rate=probe.getframerate()
                                )
                        controller.revise(PartialTranscript(
                            text, probe_number, stable=True, prosody=prosody
                        ))
                    revised_events = controller.observe(active=active, at_ms=index * self.frame_ms)
                    events += revised_events
                    self.endpoint_events.extend(revised_events)
                if any(event.event is EndpointEvent.TURN_COMMITTED for event in events):
                    committed = True
                    self.provisional_transcript = controller.partial.text.strip() or None
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=1)
            executor.shutdown(wait=True, cancel_futures=True)
            for snapshot in snapshots:
                snapshot.unlink(missing_ok=True)
        self._write_wave(self.destination, b"".join(frames))
        if not committed and not frames:
            raise RuntimeError("semantic ALSA capture produced no audio")
        return self.destination


@dataclass(frozen=True)
class WholeFileTurnDetector:
    """Treat a prerecorded file as one turn; useful for non-WAV fixtures."""

    def detect(self, audio_path: Path) -> AudioTurn | None:
        return AudioTurn(audio_path) if audio_path.stat().st_size else None


@dataclass(frozen=True)
class WaveEnergyTurnDetector:
    """Dependency-free RMS VAD for PCM WAV development recordings."""

    threshold: int = 250
    frame_ms: int = 30
    hangover_ms: int = 450

    def detect(self, audio_path: Path) -> AudioTurn | None:
        with wave.open(str(audio_path), "rb") as stream:
            rate = stream.getframerate()
            width = stream.getsampwidth()
            channels = stream.getnchannels()
            frames_per_chunk = max(1, rate * self.frame_ms // 1000)
            active: list[int] = []
            index = 0
            while chunk := stream.readframes(frames_per_chunk):
                if pcm_rms(chunk, width, channels) >= self.threshold:
                    active.append(index)
                index += 1
        if not active:
            return None
        pad = max(0, self.hangover_ms // self.frame_ms)
        start = max(0, active[0] - pad) * self.frame_ms / 1000
        end = min(index, active[-1] + pad + 1) * self.frame_ms / 1000
        return AudioTurn(audio_path, start, end)
