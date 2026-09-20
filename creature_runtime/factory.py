from __future__ import annotations

from pathlib import Path

from .adapters.local import StaticTranscriber, WhisperCppTranscriber
from .adapters.openai_cloud import OpenAITranscriber
from .adapters.openai_cloud import OpenAILoreResponder, OpenAITTS
from .adapters.elevenlabs_cloud import ElevenLabsMourningColossusTTS
from .adapters.elevenlabs_streaming import ElevenLabsDialogueStreamer
from .audio import WaveEnergyTurnDetector, WholeFileTurnDetector
from .config import RuntimeConfig
from .motion import SafeMotionRequestAdapter
from .latency import LocalLatencyMasker
from .playback import AlsaStreamingPCMPlayer, StreamingPCMPlayer, SubprocessAudioPlayer
from .responders import LoreGroundedLocalResponder
from .runtime import CreatureRuntime
from .speech import RequestOnlyTTS
from .state import ConversationState
from .models import VocalContext
from .acoustic_reference import PlaybackReferenceRing


def build_runtime(config: RuntimeConfig, *, root: Path) -> CreatureRuntime:
    lore_path = root / "frankenstein_monster_lore_emotion_interactivity.md"
    if config.responder == "local":
        responder = LoreGroundedLocalResponder()
    elif config.responder == "openai":
        responder = OpenAILoreResponder(lore_path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"unsupported responder: {config.responder}")

    if config.tts == "request_only":
        tts = RequestOnlyTTS(config.voice)
    elif config.tts == "openai":
        tts = OpenAITTS(root / "creature-reply.mp3", voice=config.voice)
    elif config.tts == "elevenlabs":
        output_path = Path(config.tts_output)
        if not output_path.is_absolute():
            output_path = root / output_path
        tts = ElevenLabsMourningColossusTTS(
            voice_id=config.voice,
            output_path=output_path,
            model_id=config.tts_model,
            api_key_env=config.tts_api_key_env,
            ffmpeg_executable=config.ffmpeg_executable,
        )
    else:
        raise ValueError(f"unsupported tts adapter: {config.tts}")

    player = SubprocessAudioPlayer(config.playback_executable) if config.playback == "ffplay" else None
    streaming_player = None
    playback_reference = PlaybackReferenceRing()
    if config.streaming_response and config.playback == "ffplay":
        streaming_player = StreamingPCMPlayer(
            config.playback_executable,
            on_write=lambda chunk, at_ms: playback_reference.record_pcm(chunk, at_ms=at_ms),
        )
    elif config.streaming_response and config.playback == "alsa":
        streaming_player = AlsaStreamingPCMPlayer(
            executable=config.playback_executable, device=config.playback_device, gain=.75
        )
        streaming_player.on_write = (
            lambda chunk, at_ms: playback_reference.record_pcm(chunk, at_ms=at_ms)
        )
    cue_directory = Path(config.cue_directory)
    if not cue_directory.is_absolute():
        cue_directory = root / cue_directory
    masker = None
    if config.latency_masking and player is not None:
        masker = LocalLatencyMasker(
            cue_directory,
            player,
            acknowledgment_delay_seconds=config.acknowledgment_delay_seconds,
            post_acknowledgment_pause_seconds=config.post_acknowledgment_pause_seconds,
        )

    streaming_output = Path(config.streaming_output)
    if not streaming_output.is_absolute():
        streaming_output = root / streaming_output
    streaming_tts = None
    if config.streaming_response:
        streaming_tts = ElevenLabsDialogueStreamer(
            voice_id=config.voice,
            ffmpeg_executable=config.ffmpeg_executable,
            api_key_env=config.tts_api_key_env,
        )

    runtime = CreatureRuntime(
        responder=responder,
        tts=tts,
        motion=SafeMotionRequestAdapter(),
        state=ConversationState(max_history=config.history_turns),
        dry_run=config.dry_run,
        latency_masker=masker,
        playback=player,
        vocal_context=VocalContext(config.mock_audience_count, config.mock_speaker_is_young),
        streaming_tts=streaming_tts,
        streaming_playback=streaming_player,
        streaming_output=streaming_output if config.streaming_response else None,
    )
    # Experimental telemetry only until installed-geometry AEC validation.
    runtime.playback_reference = playback_reference
    return runtime


def build_audio_adapters(config: RuntimeConfig, *, energy_threshold: int = 250):
    if config.turn_detector == "wave_energy":
        detector = WaveEnergyTurnDetector(threshold=energy_threshold)
    else:
        detector = WholeFileTurnDetector()

    if config.transcriber == "mock":
        transcriber = StaticTranscriber(config.mock_transcript)
    elif config.transcriber == "whisper_cpp":
        transcriber = WhisperCppTranscriber(config.whisper_executable, config.whisper_model)
    else:
        transcriber = OpenAITranscriber()
    return detector, transcriber
