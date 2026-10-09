from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Thread

from .duplex import BargeInDecision, BargeInSupervisor, CalibratedBargeInGate
from .models import CreatureTurn
from .runtime import CreatureRuntime, SpeechInterrupted


@dataclass
class InterruptibleReplyTask:
    """Run one spoken reply while a duplex capture loop watches for barge-in.

    This is intentionally transport-free. ALSA/ReSpeaker code feeds residual
    frames into ``observe_residual``; the task owns only reply cancellation and
    the truthful promotion boundary for conversation state.
    """

    runtime: CreatureRuntime
    gate: CalibratedBargeInGate
    _done: Event = field(default_factory=Event, init=False, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)
    _turn: CreatureTurn | None = field(default=None, init=False, repr=False)
    _error: BaseException | None = field(default=None, init=False, repr=False)
    supervisor: BargeInSupervisor = field(init=False)

    def __post_init__(self) -> None:
        self.supervisor = BargeInSupervisor(self.gate, self.runtime.interrupt_speech)

    def start(self, visitor_text: str) -> None:
        if self._thread is not None:
            raise RuntimeError("reply task has already started")

        def run() -> None:
            try:
                self._turn = self.runtime.handle_text(visitor_text)
            except BaseException as exc:
                self._error = exc
            finally:
                self._done.set()

        self._thread = Thread(target=run, name="creature-reply", daemon=True)
        self._thread.start()

    def observe_residual(self, rms: int, *, at_ms: int) -> BargeInDecision | None:
        return self.supervisor.observe_residual(rms, at_ms=at_ms)

    def wait(self, timeout: float = 10) -> CreatureTurn:
        if not self._done.wait(timeout):
            raise TimeoutError("reply task did not settle")
        assert self._thread is not None
        self._thread.join(timeout=0)
        if self._error is not None:
            raise self._error
        if self._turn is None:
            raise SpeechInterrupted("reply ended without a completed turn")
        return self._turn

    @property
    def interrupted(self) -> bool:
        return isinstance(self._error, SpeechInterrupted)

    @property
    def done(self) -> bool:
        return self._done.is_set()
