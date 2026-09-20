from __future__ import annotations

import subprocess
import threading
import time
from array import array
from typing import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SubprocessAudioPlayer:
    """Interruptible, non-shell audio playback with no hardware-control capability."""

    executable: str = "ffplay"
    crossfade_seconds: float = 0.3
    _process: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _spawn(self, path: Path, *, fade_in: bool = False) -> subprocess.Popen[bytes]:
        command = [self.executable, "-nodisp", "-autoexit", "-loglevel", "error"]
        if fade_in:
            command.extend(["-af", f"afade=t=in:d={self.crossfade_seconds}"])
        command.append(str(path))
        return subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes] | None) -> None:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

    def start(self, path: Path) -> None:
        self.interrupt()
        with self._lock:
            self._process = self._spawn(path)

    def crossfade_to(self, path: Path) -> None:
        with self._lock:
            previous = self._process
            current = self._spawn(path, fade_in=True)
            self._process = current
        time.sleep(self.crossfade_seconds)
        self._terminate(previous)

    def interrupt(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
        self._terminate(process)

    def play_until(self, path: Path, stop: threading.Event) -> None:
        self.interrupt()
        with self._lock:
            process = self._spawn(path)
            self._process = process
        while not stop.wait(0.02):
            if process.poll() is not None:
                break
        if stop.is_set():
            self._terminate(process)
            with self._lock:
                if self._process is process:
                    self._process = None


@dataclass
class NullSpeechPlayback:
    requested: list[Path] = field(default_factory=list)

    def start(self, path: Path) -> None:
        self.requested.append(path)

    def interrupt(self) -> None:
        return None

    def crossfade_to(self, path: Path) -> None:
        self.requested.append(path)


@dataclass
class StreamingPCMPlayer:
    """Interruptible raw-PCM sink; it contains no GPIO or motion transport."""

    executable: str = "ffplay"
    sample_rate: int = 44100
    channels: int = 1
    process_factory: Callable = subprocess.Popen
    on_write: Callable[[bytes, int], None] | None = None
    _process: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _accepting: bool = field(default=False, init=False, repr=False)

    def start(self) -> None:
        self.interrupt()
        process = self.process_factory(
            [
                self.executable,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "error",
                "-f",
                "s16le",
                "-ar",
                str(self.sample_rate),
                "-ac",
                str(self.channels),
                "pipe:0",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._process = process
            self._accepting = True

    def write(self, chunk: bytes) -> bool:
        with self._lock:
            process = self._process
            if not self._accepting:
                return False
            if process is None or process.stdin is None or process.poll() is not None:
                self._accepting = False
                return False
            try:
                process.stdin.write(chunk)
                process.stdin.flush()
                if self.on_write is not None:
                    self.on_write(chunk, int(time.monotonic() * 1000))
            except BrokenPipeError:
                self._accepting = False
                return False
            return True

    def finish(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
            self._accepting = False
        if process is None:
            return
        if process.stdin is not None and not process.stdin.closed:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=1)

    def interrupt(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
            self._accepting = False
        if process is None:
            return
        if process.stdin is not None and not process.stdin.closed:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        SubprocessAudioPlayer._terminate(process)


@dataclass
class AlsaStreamingPCMPlayer(StreamingPCMPlayer):
    """Streaming PCM playback through one explicit ALSA device."""

    device: str = "plughw:2,0"
    executable: str = "aplay"
    gain: float = .75

    def write(self, chunk: bytes) -> bool:
        return super().write(scale_s16le(chunk, self.gain))

    def start(self) -> None:
        self.interrupt()
        process = self.process_factory(
            [self.executable, "-q", "-D", self.device, "-f", "S16_LE", "-r",
             str(self.sample_rate), "-c", str(self.channels)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._process = process
            self._accepting = True


def scale_s16le(chunk: bytes, gain: float) -> bytes:
    if not 0 < gain <= 1:
        raise ValueError("PCM gain must be greater than zero and at most one")
    if len(chunk) % 2:
        raise ValueError("signed 16-bit PCM must contain complete samples")
    samples = array("h"); samples.frombytes(chunk)
    for index, sample in enumerate(samples):
        samples[index] = max(-32768, min(32767, round(sample * gain)))
    return samples.tobytes()


def fade_out_s16le(chunk: bytes, *, target_samples: int | None = None) -> bytes:
    """Return a short, monotonic PCM decrescendo for an interrupted utterance.

    A modest linear stretch lets the audible release outlast the decoder's
    last buffer without replaying an abrupt loop of speech.
    """
    if len(chunk) % 2:
        raise ValueError("signed 16-bit PCM must contain complete samples")
    samples = array("h"); samples.frombytes(chunk)
    if not samples:
        return b""
    length = len(samples) if target_samples is None else target_samples
    if length < 1:
        raise ValueError("fade target must contain at least one sample")
    source = samples
    samples = array("h")
    for index in range(length):
        position = index * (len(source) - 1) / max(1, length - 1)
        left = int(position)
        right = min(left + 1, len(source) - 1)
        fraction = position - left
        sample = round(source[left] * (1 - fraction) + source[right] * fraction)
        samples.append(round(sample * (1 - index / max(1, length - 1))))
    return samples.tobytes()


@dataclass(frozen=True)
class AlsaPCMFilePlayer:
    """Play a completed raw-PCM file through one explicit ALSA device."""

    device: str = "plughw:2,0"
    gain: float = 0.75
    executable: str = "aplay"

    def play(self, path: Path) -> None:
        if not path.is_file(): raise FileNotFoundError(path)
        process = subprocess.Popen([self.executable, "-q", "-D", self.device, "-f", "S16_LE", "-r", "44100", "-c", "1"],
                                   stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert process.stdin is not None
        try:
            with path.open("rb") as source:
                while chunk := source.read(16384): process.stdin.write(scale_s16le(chunk, self.gain))
            process.stdin.close()
            if process.wait(timeout=60) != 0: raise RuntimeError("ALSA playback failed")
        finally:
            if process.poll() is None: process.terminate(); process.wait(timeout=2)


@dataclass
class AlsaMediaCuePlayer:
    """Interruptible MP3/WAV cue playback through an explicit ALSA device."""

    device: str = "plughw:2,0"
    gain: float = 0.75
    ffmpeg_executable: str = "ffmpeg"
    aplay_executable: str = "aplay"
    _decoder: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)
    _sink: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _stop_processes(self) -> None:
        with self._lock:
            decoder, sink = self._decoder, self._sink
            self._decoder = self._sink = None
        for process in (decoder, sink):
            SubprocessAudioPlayer._terminate(process)

    def play_until(
        self,
        path: Path,
        stop: threading.Event,
        *,
        interruption_cue: Path | None = None,
        interruption_cue_gain: float = .12,
    ) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        self._stop_processes()
        decoder = subprocess.Popen(
            [self.ffmpeg_executable, "-nostdin", "-hide_banner", "-loglevel", "error",
             "-i", str(path), "-f", "s16le", "-ar", "44100", "-ac", "1", "pipe:1"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        assert decoder.stdout is not None
        sink = subprocess.Popen(
            [self.aplay_executable, "-q", "-D", self.device, "-f", "S16_LE", "-r", "44100", "-c", "1"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        assert sink.stdin is not None
        with self._lock:
            self._decoder, self._sink = decoder, sink
        last_chunk = b""
        interrupted = False
        try:
            while not stop.is_set():
                chunk = decoder.stdout.read(8192)
                if not chunk:
                    break
                last_chunk = chunk
                sink.stdin.write(scale_s16le(chunk, self.gain))
            if stop.is_set():
                # Preserve a tiny, audible release rather than killing the
                # loudspeaker at an arbitrary waveform edge. The decoder is
                # stopped first so no later speech can escape the interruption.
                interrupted = True
                SubprocessAudioPlayer._terminate(decoder)
                if not sink.stdin.closed and last_chunk:
                    # 280 ms is long enough to read as a checked, bodily
                    # release, while remaining below a conversational beat.
                    sink.stdin.write(scale_s16le(
                        fade_out_s16le(last_chunk, target_samples=12348), self.gain
                    ))
            if not sink.stdin.closed:
                sink.stdin.close()
            if interrupted:
                sink.wait(timeout=2)
            else:
                decoder.wait(timeout=5)
                sink.wait(timeout=10)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            self._stop_processes()
        finally:
            with self._lock:
                if self._decoder is decoder: self._decoder = None
                if self._sink is sink: self._sink = None
        if interrupted and interruption_cue is not None:
            if not 0 < interruption_cue_gain <= 1:
                raise ValueError("interruption cue gain must be greater than zero and at most one")
            AlsaMediaCuePlayer(
                self.device, self.gain * interruption_cue_gain,
                self.ffmpeg_executable, self.aplay_executable,
            ).play(interruption_cue)

    def play(self, path: Path) -> None:
        self.play_until(path, threading.Event())
