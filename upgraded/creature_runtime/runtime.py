from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading

from .incremental import stable_clauses
from .models import CreatureTurn, SpeechRequest, VocalContext
from .ports import AudioInput, LatencyMasking, MotionOutput, ResponseGenerator, SpeechPlayback, TextToSpeech, Transcriber, TurnDetector
from .state import ConversationState


class SpeechInterrupted(RuntimeError):
    """A visitor began a new turn before this reply was fully heard."""


@dataclass
class CreatureRuntime:
    responder: ResponseGenerator
    tts: TextToSpeech
    motion: MotionOutput
    state: ConversationState
    dry_run: bool = True
    latency_masker: LatencyMasking | None = None
    playback: SpeechPlayback | None = None
    vocal_context: VocalContext = VocalContext()
    streaming_tts: object | None = None
    streaming_playback: object | None = None
    streaming_output: Path | None = None
    last_streaming_timing: object | None = None
    _speech_cancelled: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    def handle_text(self, visitor_text: str) -> CreatureTurn:
        visitor_text = visitor_text.strip()
        if not visitor_text:
            raise ValueError("visitor text must not be empty")
        if self.streaming_tts is not None:
            return self._handle_text_streaming(visitor_text)
        masking = None
        if self.latency_masker is not None and not self.dry_run:
            masking = self.latency_masker.begin(self.state.preview_emotion(visitor_text))
        try:
            plan = self.responder.generate(visitor_text, self.state)
            motion_request = self.motion.request(plan.motion, dry_run=self.dry_run)
            speech_request = self.tts.request(
                plan.text, plan.emotion, dry_run=self.dry_run, context=self.vocal_context
            )
            if self.playback is not None and not self.dry_run and speech_request.output_path:
                output_path = Path(speech_request.output_path)
                if masking is not None:
                    masking.handoff()
                    masking = None
                self.playback.start(output_path)
        finally:
            if masking is not None:
                masking.stop()
        self.state.remember(visitor_text, plan.text)
        return CreatureTurn(visitor_text, plan.text, plan.emotion, motion_request, speech_request)

    def _handle_text_streaming(self, visitor_text: str) -> CreatureTurn:
        generate_stream = getattr(self.responder, "generate_stream", None)
        if generate_stream is None:
            raise RuntimeError("streaming TTS requires a streaming response generator")
        destination = self.streaming_output
        if destination is None:
            raise RuntimeError("streaming output path is not configured")

        self._speech_cancelled.clear()
        masking = None
        if self.latency_masker is not None and not self.dry_run:
            masking = self.latency_masker.begin(self.state.preview_emotion(visitor_text))
        plan = generate_stream(visitor_text, self.state)
        collected: list[str] = []

        def clauses():
            for clause in stable_clauses(plan.chunks):
                if self._speech_cancelled.is_set():
                    raise SpeechInterrupted("visitor interrupted before reply completion")
                collected.append(clause)
                yield clause

        first_audio = threading.Lock()
        playback_started = False
        playback_finished = False
        stream_succeeded = False

        def consume_audio(chunk: bytes) -> None:
            nonlocal masking, playback_started
            if self._speech_cancelled.is_set():
                return
            if self.streaming_playback is None:
                return
            with first_audio:
                if not playback_started:
                    if masking is not None:
                        masking.handoff()
                        masking = None
                    self.streaming_playback.start()
                    playback_started = True
            self.streaming_playback.write(chunk)

        try:
            self.last_streaming_timing = self.streaming_tts.stream_to_pcm(
                clauses(),
                plan.emotion,
                destination,
                context=self.vocal_context,
                on_processed_chunk=consume_audio,
            )
            if self._speech_cancelled.is_set():
                raise SpeechInterrupted("visitor interrupted before reply completion")
            stream_succeeded = True
            if playback_started:
                self.streaming_playback.finish()
                playback_finished = True
        finally:
            if masking is not None:
                masking.stop()
            if playback_started and not playback_finished:
                self.streaming_playback.interrupt()
            # A cancelled or otherwise failed stream must not leave a raw
            # partial reply on disk. Successfully completed exchange audio is
            # handled by the caller's encrypted archive flow.
            if not stream_succeeded:
                destination.unlink(missing_ok=True)

        reply = " ".join(collected)
        # Do not promote an unheard reply into the Creature's memory or motion
        # vocabulary. A barge-in begins a new visitor turn instead.
        if self._speech_cancelled.is_set():
            raise SpeechInterrupted("visitor interrupted before reply completion")
        motion_request = self.motion.request(plan.motion, dry_run=self.dry_run)
        speech_request = SpeechRequest(
            reply,
            type(self.streaming_tts).__name__,
            "mourning-colossus-streaming",
            self.dry_run,
            str(destination),
        )
        self.state.remember(visitor_text, reply)
        return CreatureTurn(visitor_text, reply, plan.emotion, motion_request, speech_request)

    def interrupt_speech(self) -> None:
        self._speech_cancelled.set()
        if self.playback is not None:
            self.playback.interrupt()
        if self.streaming_playback is not None:
            self.streaming_playback.interrupt()

    def handle_audio(
        self, source: AudioInput, detector: TurnDetector, transcriber: Transcriber
    ) -> CreatureTurn | None:
        audio_path = source.capture()
        audio_turn = detector.detect(audio_path)
        if audio_turn is None:
            return None
        return self.handle_text(transcriber.transcribe(audio_turn))
