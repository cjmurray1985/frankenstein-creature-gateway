from __future__ import annotations

from dataclasses import dataclass, field

from .models import Emotion

KIND_WORDS = frozenset({"friend", "kind", "listen", "sorry", "welcome", "understand", "stay", "hello"})
HOSTILE_WORDS = frozenset({"monster", "ugly", "hate", "kill", "stupid", "leave", "mock", "freak"})


@dataclass
class ConversationState:
    emotion: Emotion = Emotion.CURIOUS
    trust: int = 0
    hurt: int = 0
    turns: list[tuple[str, str]] = field(default_factory=list)
    durable_memories: list[str] = field(default_factory=list)
    max_history: int = 8

    def preview_emotion(self, visitor_text: str) -> Emotion:
        preview = ConversationState(
            emotion=self.emotion,
            trust=self.trust,
            hurt=self.hurt,
            turns=list(self.turns),
            durable_memories=list(self.durable_memories),
            max_history=self.max_history,
        )
        return preview.observe(visitor_text)

    def observe(self, visitor_text: str) -> Emotion:
        words = {word.strip(".,!?;:'\"").lower() for word in visitor_text.split()}
        kindness = len(words & KIND_WORDS)
        hostility = len(words & HOSTILE_WORDS)
        self.trust = max(-4, min(4, self.trust + kindness - hostility))
        self.hurt = max(0, min(4, self.hurt + hostility - kindness))

        first_encounter = not self.turns
        if self.hurt >= 3:
            self.emotion = Emotion.WITHDRAWN if self.trust <= -2 else Emotion.ANGRY
        elif hostility:
            self.emotion = Emotion.HURT if self.trust >= 0 else Emotion.WARY
        elif kindness and first_encounter:
            self.emotion = Emotion.HOPEFUL
        elif self.trust >= 3:
            self.emotion = Emotion.ENGAGED
        elif kindness:
            self.emotion = Emotion.HOPEFUL
        elif self.turns:
            self.emotion = Emotion.ENGAGED if self.trust >= 0 else Emotion.WARY
        else:
            self.emotion = Emotion.CURIOUS
        return self.emotion

    def remember(self, visitor_text: str, reply: str) -> None:
        self.turns.append((visitor_text, reply))
        if len(self.turns) > self.max_history:
            del self.turns[:-self.max_history]
