from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .audio import AlsaSemanticTurnAudioInput
from .adapters.local import WhisperCppTranscriber
from .config import RuntimeConfig
from .factory import build_audio_adapters, build_runtime
from .latency import LocalLatencyMasker
from .models import AudioTurn
from .endpointing import EndpointController
from .playback import AlsaMediaCuePlayer, AlsaPCMFilePlayer
from .records import ConversationArchiveSession, EncryptedConversationStore, ParticipantRecord
from .session import ConversationSessionController
from .speech_archive import EncryptedSpeechStore
from .memory import IndividualMemoryStore, extract_explicit_facts


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run one bounded live multi-turn Creature encounter"
    )
    result.add_argument("--config", type=Path, required=True)
    result.add_argument("--capture-dir", type=Path, required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument("--record-dir", type=Path, required=True)
    result.add_argument("--speech-dir", type=Path, required=True)
    result.add_argument("--turns", type=int, default=2)
    result.add_argument("--device", default="plughw:2,0")
    result.add_argument("--max-duration", type=int, default=30)
    result.add_argument("--end-silence-ms", type=int, default=4500)
    result.add_argument("--threshold", type=int, default=120)
    result.add_argument("--gain", type=float, default=.75)
    result.add_argument("--speaker-id", default="visitor-1")
    result.add_argument("--speaker-label", default="my friend")
    result.add_argument("--memory-dir", type=Path,
                        help="encrypted durable memory directory for the explicit speaker id")
    result.add_argument("--key-env", default="CREATURE_RECORD_KEY")
    result.add_argument("--operator-gated", action="store_true")
    result.add_argument(
        "--retain-plaintext-diagnostics", action="store_true",
        help="retain raw WAV/PCM after encrypted archival (private diagnostics only)",
    )
    result.add_argument("--opening-cue", type=Path,
                        help="Creature-spoken invitation played once before the first listening window")
    result.add_argument("--listen-cue", type=Path,
                        help="deprecated nonverbal cue; prefer --opening-cue")
    result.add_argument("--latency-cues", type=Path,
                        help="cue library used to embody response-generation delays")
    result.add_argument("--acoustic-settle-ms", type=int, default=350,
                        help="speaker ring-down delay before opening the microphone")
    return result


def assemble_exchange(
    captures: list[Path], replies: list[Path], destination: Path, ffmpeg: str
) -> None:
    if not captures or len(captures) != len(replies):
        raise ValueError("exchange audio requires matching capture and reply files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for capture, reply in zip(captures, replies):
        command.extend(["-i", str(capture), "-f", "s16le", "-ar", "44100", "-ac", "1", "-i", str(reply)])
    labels = []
    filters = []
    for index in range(len(captures) * 2):
        label = f"a{index}"
        filters.append(f"[{index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono[{label}]")
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]")
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[out]", "-codec:a", "libmp3lame",
        "-b:a", "160k", "-write_id3v2", "1", str(destination),
    ])
    subprocess.run(command, check=True, timeout=120)
    if not destination.is_file() or not destination.read_bytes().startswith(b"ID3"):
        raise RuntimeError("exchange assembly did not create an ID3-tagged MP3")


def valid_transcript(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    marker = cleaned.upper().replace(" ", "_")
    if marker in {"[BLANK_AUDIO]", "[SILENCE]", "[INAUDIBLE]", "BLANK_AUDIO", "SILENCE", "INAUDIBLE"}:
        return None
    # whisper.cpp represents non-lexical audio as a wholly bracketed caption;
    # such annotations are never visitor dialogue.
    if re.fullmatch(r"[\[(].*[\])]", cleaned, re.DOTALL):
        return None
    if re.fullmatch(
        r"[\[(]\s*(?:(?:dramatic|background)\s+)?(?:music(?:\s+playing)?|silence|applause|noise|sound(?:s)?)\s*[\])]",
        cleaned,
        re.IGNORECASE,
    ):
        return None
    return cleaned


def authoritative_audio_turn(audio_path: Path, detected: AudioTurn | None) -> AudioTurn | None:
    """Validate speech presence without re-cropping an already endpointed turn."""
    return None if detected is None else AudioTurn(audio_path)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 1 <= args.turns <= 4:
        raise ValueError("turn count must be between 1 and 4")
    if not 0 <= args.acoustic_settle_ms <= 2000:
        raise ValueError("acoustic settle delay must be between 0 and 2000 ms")

    root = Path(__file__).resolve().parent.parent
    config = RuntimeConfig.load(args.config)
    record_id = datetime.now(timezone.utc).strftime("live-%Y%m%d-%H%M%S")
    runtime = build_runtime(config, root=root)
    memory_store = IndividualMemoryStore(args.memory_dir, key_env=args.key_env) if args.memory_dir else None
    if memory_store is not None:
        runtime.state.durable_memories = [
            fact.text for fact in memory_store.recall(args.speaker_id, record_id)
        ]
    detector, transcriber = build_audio_adapters(config, energy_threshold=args.threshold)
    provisional_transcriber = transcriber
    if config.transcriber == "whisper_cpp" and config.provisional_whisper_model:
        provisional_transcriber = WhisperCppTranscriber(
            config.whisper_executable, config.provisional_whisper_model
        )
    player = AlsaPCMFilePlayer(args.device, args.gain)
    cue_player = AlsaMediaCuePlayer(
        args.device, args.gain, ffmpeg_executable=config.ffmpeg_executable
    )
    latency_masker = None
    if args.latency_cues is not None:
        latency_masker = LocalLatencyMasker(
            args.latency_cues, cue_player,
            acknowledgment_delay_seconds=config.acknowledgment_delay_seconds,
            post_acknowledgment_pause_seconds=config.post_acknowledgment_pause_seconds,
        )
        # The live CLI starts masking at acoustic turn commit so it covers STT
        # as well as response/TTS latency. Avoid starting a second masker later.
        runtime.latency_masker = None
    participant = ParticipantRecord(args.speaker_id, args.speaker_label)
    records = EncryptedConversationStore(args.record_dir, key_env=args.key_env)
    speech_store = EncryptedSpeechStore(args.speech_dir, key_env=args.key_env)
    # Fail before opening the microphone if a successful encounter could not
    # be archived according to the private-record contract.
    records.validate_key()
    speech_store.validate_key()
    archive = ConversationArchiveSession(record_id=record_id)
    lifecycle = ConversationSessionController(records, (participant,), archive=archive)
    captures: list[Path] = []
    replies: list[Path] = []

    if args.opening_cue is not None:
        print(json.dumps({"status": "opening_invitation"}), flush=True)
        cue_player.play(args.opening_cue)
        time.sleep(args.acoustic_settle_ms / 1000)

    for turn_number in range(1, args.turns + 1):
        capture = args.capture_dir / f"{record_id}-turn-{turn_number}.wav"
        reply = args.output_dir / f"{record_id}-turn-{turn_number}.pcm"
        runtime.streaming_output = reply
        source = AlsaSemanticTurnAudioInput(
            destination=capture,
            provisional_transcriber=lambda path: provisional_transcriber.transcribe(
                detector.detect(path) or AudioTurn(path)
            ),
            device=args.device,
            max_duration_seconds=args.max_duration,
            threshold=args.threshold,
            controller_factory=lambda: EndpointController(
                patient_commit_ms=args.end_silence_ms,
                exceptional_commit_ms=max(8000, args.end_silence_ms),
            ),
        )
        if args.operator_gated:
            print(json.dumps({"status": "armed", "turn": turn_number, "turns": args.turns}), flush=True)
            input()
        if args.listen_cue is not None:
            print(json.dumps({"status": "listen_cue", "turn": turn_number}), flush=True)
            player.play(args.listen_cue)
            time.sleep(args.acoustic_settle_ms / 1000)
        print(json.dumps({"status": "listening", "turn": turn_number, "turns": args.turns}), flush=True)
        lifecycle.begin_turn()
        masking = None
        try:
            audio_path = source.capture()
            if latency_masker is not None:
                masking = latency_masker.begin(runtime.state.emotion)
            audio_turn = authoritative_audio_turn(audio_path, detector.detect(audio_path))
            if audio_turn is None:
                raise RuntimeError("no speech detected")
            # The small provisional model decides only when the visitor has
            # finished. The configured full model remains authoritative for
            # semantic details such as names, yes/no answers, and negation.
            transcript = valid_transcript(transcriber.transcribe(audio_turn))
            if transcript is None:
                raise RuntimeError("transcriber returned silence")
            completed = runtime.handle_text(transcript)
            if masking is not None:
                masking.handoff()
            lifecycle.complete_turn(completed, args.speaker_id)
        except BaseException:
            if masking is not None:
                masking.stop()
            lifecycle.abandon_turn()
            capture.unlink(missing_ok=True)
            reply.unlink(missing_ok=True)
            raise
        captures.append(capture)
        replies.append(reply)
        print(json.dumps({
            "status": "speaking", "turn": turn_number, "transcript": completed.visitor_text,
            "reply": completed.reply, "emotion": completed.emotion.value,
            "motion_intent": completed.motion_request.intent.value,
        }), flush=True)
        # Streaming replies have already been spoken chunk-by-chunk. Replaying
        # their completed PCM file would duplicate the Creature's answer.
        if runtime.streaming_tts is None:
            player.play(reply)
        if turn_number < args.turns:
            time.sleep(args.acoustic_settle_ms / 1000)

    record = lifecycle.end()
    if record is None:
        raise RuntimeError("session ended without a completed turn")
    exchange = args.output_dir / f"{record_id}-exchange.mp3"
    try:
        assemble_exchange(captures, replies, exchange, config.ffmpeg_executable)
        speech_store.write(record_id, exchange.read_bytes())
        # A visitor fact becomes durable only after both the finalized record
        # and the actually played exchange have been archived successfully.
        if memory_store is not None:
            for archived_turn in record.turns:
                for fact in extract_explicit_facts(archived_turn.visitor_text, record.record_id):
                    memory_store.remember(args.speaker_id, fact)
    finally:
        if exchange.exists():
            exchange.unlink()
        if not args.retain_plaintext_diagnostics:
            for plaintext in (*captures, *replies):
                plaintext.unlink(missing_ok=True)
    print(json.dumps({
        "status": "archived", "record_id": record.record_id, "turn_count": len(record.turns),
        "emotional_summary": record.emotional_summary, "encrypted_audio": True,
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
