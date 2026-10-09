from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class EndpointEvent(str, Enum):
    SPEECH_STARTED = "speech_started"
    TENTATIVE_END = "tentative_end"
    SPEECH_RESUMED = "speech_resumed"
    TURN_COMMITTED = "turn_committed"


@dataclass(frozen=True)
class EndpointDecision:
    event: EndpointEvent
    at_ms: int
    generation: int
    reason: str
    transcript: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class PartialTranscript:
    text: str
    revision: int
    stable: bool = False
    prosody: str = "unknown"


class HeuristicTurnCompletionScorer:
    """Replaceable, conservative local completeness scorer.

    It is deliberately a gate, not a language model. Ambiguous language falls
    back to the patient timeout instead of being treated as a completed turn.
    """

    _INCOMPLETE = re.compile(
        r"(?:\b(?:and|but|because|if|or|so|that|the|a|an|to|of|for|with|when|while|then)|"
        r"[,;:\-–—…])\s*$",
        re.IGNORECASE,
    )
    _FILLER = re.compile(r"\b(?:uh+|um+|hmm+|let me|I mean)\s*[.…]*$", re.IGNORECASE)

    def score(self, text: str) -> tuple[float, str]:
        cleaned = " ".join(text.strip().split())
        if not cleaned or re.fullmatch(r"[\[(].*[\])]", cleaned, re.DOTALL):
            return 0.0, "nonlexical"
        if self._INCOMPLETE.search(cleaned) or self._FILLER.search(cleaned):
            return 0.12, "linguistically_incomplete"
        if cleaned.lower().rstrip(".!?") in {"yes", "no", "I will", "I do", "perhaps", "never"}:
            return 0.97, "complete_short_answer"
        if cleaned.endswith("?"):
            return 0.96, "complete_question"
        if cleaned.endswith("!"):
            return 0.90, "complete_exclamation"
        if cleaned.endswith("."):
            if len(cleaned.split()) <= 6:
                return 0.91, "brief_declarative"
            # ASR frequently inserts a period during a thoughtful pause. Long
            # declarations need stronger evidence or the patient timeout.
            return 0.78, "declarative_pause_ambiguous"
        return 0.62, "ambiguous_no_terminal"


class EndpointController:
    """Deterministic semantic/acoustic turn state machine.

    Call ``observe`` for every fixed-duration audio frame and ``revise`` when a
    provisional ASR result arrives. The controller has no playback, archive,
    network, motion, or GPIO capability.
    """

    def __init__(
        self,
        *,
        tentative_silence_ms: int = 450,
        fast_commit_ms: int = 900,
        patient_commit_ms: int = 4500,
        exceptional_commit_ms: int = 8000,
        completion_threshold: float = 0.88,
        scorer: HeuristicTurnCompletionScorer | None = None,
    ) -> None:
        if not 0 < tentative_silence_ms <= fast_commit_ms <= patient_commit_ms <= exceptional_commit_ms:
            raise ValueError("endpoint timing must be ordered and positive")
        self.tentative_silence_ms = tentative_silence_ms
        self.fast_commit_ms = fast_commit_ms
        self.patient_commit_ms = patient_commit_ms
        self.exceptional_commit_ms = exceptional_commit_ms
        self.completion_threshold = completion_threshold
        self.scorer = scorer or HeuristicTurnCompletionScorer()
        self.speaking = False
        self.committed = False
        self.silence_started_ms: int | None = None
        self.tentative_emitted = False
        self.generation = 0
        self.partial = PartialTranscript("", 0)
        self._last_normalized = ""
        self._stable_revisions = 0

    def revise(self, partial: PartialTranscript) -> None:
        if partial.revision <= self.partial.revision:
            return
        normalized = " ".join(partial.text.strip().split()).casefold()
        self._stable_revisions = (
            2 if partial.stable else
            (self._stable_revisions + 1 if normalized == self._last_normalized else 1)
        )
        self._last_normalized = normalized
        self.partial = partial

    def observe(self, *, active: bool, at_ms: int) -> list[EndpointDecision]:
        if self.committed:
            return []
        events: list[EndpointDecision] = []
        if active:
            if not self.speaking:
                event = EndpointEvent.SPEECH_RESUMED if self.tentative_emitted else EndpointEvent.SPEECH_STARTED
                if event is EndpointEvent.SPEECH_RESUMED:
                    self.generation += 1
                    self.partial = PartialTranscript("", self.partial.revision)
                    self._last_normalized = ""
                    self._stable_revisions = 0
                events.append(EndpointDecision(event, at_ms, self.generation, event.value))
            self.speaking = True
            self.silence_started_ms = None
            self.tentative_emitted = False
            return events

        if not self.speaking and self.silence_started_ms is None:
            return events
        if self.speaking:
            self.speaking = False
            self.silence_started_ms = at_ms
        assert self.silence_started_ms is not None
        silence = at_ms - self.silence_started_ms
        score, reason = self.scorer.score(self.partial.text)
        if reason == "complete_question" and self.partial.prosody not in {"rising", "level"}:
            score, reason = 0.75, "question_without_terminal_rise"
        if silence >= self.tentative_silence_ms and not self.tentative_emitted:
            self.tentative_emitted = True
            events.append(EndpointDecision(
                EndpointEvent.TENTATIVE_END, at_ms, self.generation, reason,
                self.partial.text, score,
            ))
        fast = silence >= self.fast_commit_ms and score >= self.completion_threshold and self._stable_revisions >= 2
        patient = silence >= self.patient_commit_ms and reason != "linguistically_incomplete"
        exceptional = silence >= self.exceptional_commit_ms
        if fast or patient or exceptional:
            self.committed = True
            why = "semantic_complete" if fast else ("patient_timeout" if patient else "exceptional_timeout")
            events.append(EndpointDecision(
                EndpointEvent.TURN_COMMITTED, at_ms, self.generation, why,
                self.partial.text, score,
            ))
        return events
