from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .models import AmbientMood, Emotion

STATE_SCHEMA_VERSION = 3
RELATIONSHIP_DECAY_WINDOW = timedelta(days=14)
MIN_TRUST = -4
MAX_TRUST = 4
MAX_HURT = 4
MAX_FAMILIARITY = 4

KIND_WORDS = frozenset({
    "friend", "kind", "listen", "sorry", "welcome", "understand", "stay", "hello",
    "excited", "glad", "happy", "curious", "connection", "thank", "thanks",
    "appreciate", "care", "good", "please", "yes", "agree", "right", "respect",
})

KINDNESS_PHRASES = (
    "you deserve kindness", "you deserve to be heard", "you deserve respect",
    "i am glad to meet you", "i'm glad to meet you", "i am glad you are here",
    "i'm glad you're here", "i am glad you came", "i'm glad you came",
    "i will stay with you", "i won't leave you", "i will not leave you",
    "you are not alone", "you're not alone", "i am here with you", "i'm here with you",
    "i am here for you", "i'm here for you", "i understand how that feels",
    "i can see why that hurt", "that must have been hard", "i am sorry that happened",
    "i'm sorry that happened", "i am listening to you", "i'm listening to you",
)

# Isolated words such as "monster" and "leave" often appear in neutral
# questions. Require a phrase that actually reads as rejection or insult.
HOSTILE_PHRASES = (
    "ugly monster", "you are ugly", "you're ugly", "i hate you", "i hate this",
    "kill you", "i will kill", "stupid freak", "you are stupid", "you're stupid",
    "shut up", "go away", "leave me alone", "get away from me", "you are a freak",
    "you're a freak", "freak", "you are a monster", "you're a monster", "i want you gone",
    "i despise you", "mock you", "make fun of you", "i wish i had never come",
    "i wish i had never met you", "i regret coming here", "i never should have come",
    "i wish i had not come", "i wish i hadn't come", "i wish you were gone",
    "you disgust me", "you make me sick", "you are repulsive", "you're repulsive",
    "nobody wants you", "no one wants you", "you do not belong here", "you don't belong here",
    "i do not want to talk to you", "i don't want to talk to you",
    "i cannot stand looking at you", "i can't stand looking at you",
    "you should never have been made", "i wish you had never been made",
)

SUSPICION_PHRASES = (
    "why should i trust", "are you lying", "prove it", "what do you really want",
    "i don't know whether i can trust you", "i do not know whether i can trust you",
    "i don't know if i can trust you", "i do not know if i can trust you",
    "i can't trust you", "i cannot trust you", "i do not trust you", "i don't trust you",
    "you frighten me", "you scare me", "i am afraid of you", "i'm afraid of you",
    "i am scared of you", "i'm scared of you", "what if you hurt me",
    "i am skeptical", "i'm skeptical", "i have doubts about you", "i doubt your story",
    "i am not convinced", "i'm not convinced", "that does not add up", "that doesn't add up",
    "your story does not add up", "your story doesn't add up", "what are you hiding",
    "what are you keeping from me", "you are hiding something", "you're hiding something",
    "i find that hard to believe", "i find it hard to believe", "sounds made up",
    "something is not right", "something's not right", "something is off about this",
)

VULNERABILITY_PHRASES = (
    "do not leave me", "don't leave me", "please stay", "please do not leave",
    "please don't leave", "stay with me",
)

STARTLE_PHRASES = (
    "what was that", "whoa", "that startled", "you startled", "i was surprised",
    "you made me jump", "that made me jump", "that caught me off guard", "that was unexpected",
)

DISAGREEMENT_PHRASES = (
    "i disagree", "i do not agree", "i don't agree", "that is not right", "that's not right",
    "you are wrong", "you're wrong", "i cannot agree", "i can't agree", "i see it differently",
    "i do not think so", "i don't think so", "i am not sure that is true", "i'm not sure that's true",
    "i cannot accept that", "i can't accept that", "that seems wrong to me",
)

PERSONAL_DISCLOSURE_PHRASES = (
    "i have felt alone", "i've felt alone", "i felt alone", "i feel alone",
    "i feel lonely", "i am lonely", "i'm lonely", "i have been lonely", "i've been lonely",
    "i was lonely", "i felt rejected",
    "i have felt rejected", "i've felt rejected", "i was bullied", "people laughed at me",
    "people judged me", "nobody understood me", "no one understood me", "i lost someone",
    "i lost a friend", "i lost my mother", "i lost my father", "i lost my brother",
    "i lost my sister", "i lost my partner", "i lost my child", "my mother died",
    "my father died", "my friend died", "i am grieving", "i'm grieving",
    "i know what it is like to be", "i know what it's like to be", "i know what it feels like",
    "i have been through that", "i've been through that", "i went through something similar",
    "this is difficult for me to say", "this is hard for me to say",
    "i do not tell people this", "i don't tell people this", "i have never told anyone",
)

_NEGATION = re.compile(r"\b(?:don't|do not|didn't|did not|isn't|is not|aren't|are not|not|never|no)\s+(?:\w+\s+){0,2}?([\w']+)\b")
_ONLY_MONSTER_REJECTION = re.compile(
    r"\byou(?:'re| are)\s+(?:(?:only|just|nothing but|nothing more than)\s+)?(?:a\s+)?monster\b"
)


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    value = _normalize_text(text)
    return any(phrase in value for phrase in phrases)


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").replace("‘", "'").split())


def _question_like(text: str) -> bool:
    value = _normalize_text(text)
    words = value.split()
    if len(words) < 3:
        return False
    question_openers = (
        "tell me ", "show me ", "describe ", "explain ", "i was wondering ",
        "i wonder ", "i would like to know ", "i'd like to know ", "could you tell me ",
        "can you tell me ", "tell me more about ", "help me understand ", "i want to ask ",
        "may i ask ", "could i ask ", "what do you mean ",
    )
    if value.startswith(question_openers):
        return True
    if words[0] in {"so", "well", "and", "but", "then"} and len(words) > 1:
        words = words[1:]
    return "?" in value or words[0] in {
        "what", "why", "how", "who", "where", "when", "which", "can", "could",
        "would", "will", "do", "does", "did", "is", "are", "have",
    }


def _kindness_count(text: str) -> int:
    value = _normalize_text(text)
    words = {word.strip(".,!?;:'\"()[]{}").lower() for word in value.split()}
    negated = {match.group(1).lower() for match in _NEGATION.finditer(value)}
    kindness = len((words & KIND_WORDS) - negated)
    # "Trust" is a positive signal only when the visitor actually expresses
    # trust; fear or uncertainty about trusting the Creature must not raise it.
    distrusting = _contains_phrase(value, SUSPICION_PHRASES)
    if not distrusting and _contains_phrase(value, ("i trust you", "i can trust you", "you have my trust")):
        kindness += 1
    if not distrusting and _contains_phrase(value, KINDNESS_PHRASES):
        kindness += 1
    return kindness


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AmbientMoodState:
    mood: AmbientMood = AmbientMood.DORMANT
    source: str = "default"
    updated_at: str | None = None


@dataclass
class RelationshipState:
    trust: int = 0
    hurt: int = 0
    familiarity: int = 0
    last_encounter_at: str | None = None
    decay_applied_at: str | None = None
    opening_residue: Emotion | None = None
    residue_strength: int = 0

    def __post_init__(self) -> None:
        self.trust = max(MIN_TRUST, min(MAX_TRUST, int(self.trust)))
        self.hurt = max(0, min(MAX_HURT, int(self.hurt)))
        self.familiarity = max(0, min(MAX_FAMILIARITY, int(self.familiarity)))
        self.residue_strength = max(0, min(2, int(self.residue_strength)))

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("relationship timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @classmethod
    def _parse_timestamp(cls, value: str) -> datetime:
        try:
            return cls._aware(datetime.fromisoformat(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("relationship timestamp is invalid") from exc

    @staticmethod
    def _toward_zero(value: int, amount: int) -> int:
        if value > 0:
            return max(0, value - amount)
        if value < 0:
            return min(0, value + amount)
        return value

    def apply_inactivity_decay(
        self,
        now: datetime,
        *,
        window: timedelta = RELATIONSHIP_DECAY_WINDOW,
    ) -> int:
        """Apply whole rolling inactivity windows without double-counting.

        The encounter timestamp is intentionally not moved here. It moves only
        when a completed encounter is committed, so a visitor who returns
        before the fourteen-day window gets a fresh window at completion.
        """
        now = self._aware(now)
        if window <= timedelta(0):
            raise ValueError("relationship decay window must be positive")
        if not self.last_encounter_at:
            return 0
        last = self._parse_timestamp(self.last_encounter_at)
        checkpoint = self._parse_timestamp(self.decay_applied_at) if self.decay_applied_at else last
        checkpoint = max(last, checkpoint)
        elapsed = now - checkpoint
        periods = int(elapsed.total_seconds() // window.total_seconds())
        if periods <= 0:
            return 0
        self.trust = self._toward_zero(self.trust, periods)
        self.hurt = max(0, self.hurt - periods)
        self.familiarity = max(0, self.familiarity - periods)
        self.decay_applied_at = (checkpoint + periods * window).isoformat()
        return periods

    def begin_encounter(self, now: datetime) -> Emotion:
        """Return and consume the visitor-specific opening posture."""
        self.apply_inactivity_decay(now)
        posture = self.opening_residue
        if posture is None:
            if self.trust <= -2:
                posture = Emotion.WARY
            elif self.trust >= 3:
                posture = Emotion.ENGAGED
            elif self.familiarity > 0 and self.trust > 0:
                posture = Emotion.ATTENTIVE
            else:
                posture = Emotion.CURIOUS
        self.opening_residue = None
        self.residue_strength = 0
        return posture

    def complete_encounter(self, now: datetime, final_emotion: Emotion) -> None:
        """Commit relationship changes and residue after a real encounter.

        Trust is deliberately protective: a fresh negative encounter costs one
        step, while harm landing on an already hurt relationship costs two.
        Kindness earns one step at a time. Ambient mood is not consulted or
        mutated here.
        """
        now = self._aware(now)
        self.apply_inactivity_decay(now)
        self.familiarity = min(MAX_FAMILIARITY, self.familiarity + 1)
        positive = final_emotion in {Emotion.HOPEFUL, Emotion.ENGAGED, Emotion.RELIEVED}
        negative = final_emotion in {
            Emotion.WARY,
            Emotion.SUSPICIOUS,
            Emotion.HURT,
            Emotion.ANGRY,
            Emotion.WITHDRAWN,
        }
        if positive:
            self.trust = min(MAX_TRUST, self.trust + 1)
            self.hurt = max(0, self.hurt - 1)
            self.opening_residue = Emotion.ENGAGED if self.trust >= 3 else Emotion.HOPEFUL
            self.residue_strength = 2
        elif negative:
            damage = 2 if self.hurt > 0 or self.trust < 0 else 1
            self.trust = max(MIN_TRUST, self.trust - damage)
            self.hurt = min(MAX_HURT, self.hurt + damage)
            self.opening_residue = Emotion.WARY if final_emotion in {
                Emotion.WARY,
                Emotion.SUSPICIOUS,
            } else Emotion.HURT
            self.residue_strength = 2
        else:
            self.opening_residue = None
            self.residue_strength = 0
        self.last_encounter_at = now.isoformat()
        self.decay_applied_at = self.last_encounter_at


@dataclass
class MomentaryEmotionState:
    emotion: Emotion = Emotion.CURIOUS


@dataclass(frozen=True)
class EmotionTransition:
    from_emotion: Emotion
    to_emotion: Emotion
    cause: str
    confidence: float
    timestamp: str
    source: str

    def __post_init__(self) -> None:
        if not self.cause.strip() or not self.source.strip() or not self.timestamp.strip():
            raise ValueError("emotion transition provenance fields must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("emotion transition confidence must be between zero and one")


@dataclass
class ConversationState:
    ambient: AmbientMoodState = field(default_factory=AmbientMoodState)
    relationship: RelationshipState = field(default_factory=RelationshipState)
    momentary: MomentaryEmotionState = field(default_factory=MomentaryEmotionState)
    turns: list[tuple[str, str]] = field(default_factory=list)
    durable_memories: list[str] = field(default_factory=list)
    transitions: list[EmotionTransition] = field(default_factory=list)
    max_history: int = 8
    max_transitions: int = 64
    timestamp_factory: Callable[[], str] = field(default=_utc_timestamp, repr=False, compare=False)

    @property
    def emotion(self) -> Emotion:
        """Compatibility view for providers and presentation adapters."""
        return self.momentary.emotion

    @emotion.setter
    def emotion(self, value: Emotion) -> None:
        self.transition_to(
            value,
            cause="legacy state assignment",
            confidence=1.0,
            source="compatibility",
        )

    @property
    def trust(self) -> int:
        """Compatibility view for the visitor relationship."""
        return self.relationship.trust

    @trust.setter
    def trust(self, value: int) -> None:
        self.relationship.trust = max(MIN_TRUST, min(MAX_TRUST, int(value)))

    @property
    def hurt(self) -> int:
        """Compatibility view for the visitor relationship."""
        return self.relationship.hurt

    @hurt.setter
    def hurt(self, value: int) -> None:
        self.relationship.hurt = max(0, min(MAX_HURT, int(value)))

    @property
    def familiarity(self) -> int:
        return self.relationship.familiarity

    def begin_encounter(self, *, at: datetime | None = None) -> Emotion:
        """Apply relationship decay and set the next opening posture."""
        now = at or datetime.now(timezone.utc)
        posture = self.relationship.begin_encounter(now)
        if posture is not self.emotion:
            self.transition_to(
                posture,
                cause="visitor relationship opening residue",
                confidence=0.90,
                source="visitor_relationship",
            )
        return posture

    def complete_encounter(self, *, at: datetime | None = None) -> Emotion:
        """Commit visitor relationship state only after a completed encounter."""
        now = at or datetime.now(timezone.utc)
        self.relationship.complete_encounter(now, self.emotion)
        return self.emotion

    def preview_emotion(self, visitor_text: str) -> Emotion:
        preview = ConversationState(
            ambient=AmbientMoodState(
                mood=self.ambient.mood,
                source=self.ambient.source,
                updated_at=self.ambient.updated_at,
            ),
            relationship=RelationshipState(
                trust=self.relationship.trust,
                hurt=self.relationship.hurt,
                familiarity=self.relationship.familiarity,
                last_encounter_at=self.relationship.last_encounter_at,
                decay_applied_at=self.relationship.decay_applied_at,
                opening_residue=self.relationship.opening_residue,
                residue_strength=self.relationship.residue_strength,
            ),
            momentary=MomentaryEmotionState(self.momentary.emotion),
            turns=list(self.turns),
            durable_memories=list(self.durable_memories),
            transitions=list(self.transitions),
            max_history=self.max_history,
            max_transitions=self.max_transitions,
            timestamp_factory=self.timestamp_factory,
        )
        return preview.observe(visitor_text)

    def transition_to(
        self,
        emotion: Emotion,
        *,
        cause: str,
        confidence: float,
        source: str,
    ) -> Emotion:
        if emotion is self.momentary.emotion:
            return emotion
        previous = self.momentary.emotion
        self.momentary.emotion = emotion
        self.transitions.append(
            EmotionTransition(
                from_emotion=previous,
                to_emotion=emotion,
                cause=cause,
                confidence=confidence,
                timestamp=self.timestamp_factory(),
                source=source,
            )
        )
        if len(self.transitions) > self.max_transitions:
            del self.transitions[:-self.max_transitions]
        return emotion

    def _transition_from_observation(
        self,
        emotion: Emotion,
        *,
        cause: str,
        confidence: float,
    ) -> Emotion:
        return self.transition_to(
            emotion,
            cause=cause,
            confidence=confidence,
            source="visitor_transcript",
        )

    def observe(self, visitor_text: str) -> Emotion:
        value = _normalize_text(visitor_text)
        kindness = _kindness_count(visitor_text)
        monster_rejection = bool(_ONLY_MONSTER_REJECTION.search(value))
        hostility = min(2, sum(phrase in value for phrase in HOSTILE_PHRASES) + int(monster_rejection))
        prior_trust = self.trust
        self.trust = self.trust + kindness - hostility
        self.hurt = self.hurt + hostility - kindness

        first_encounter = not self.turns
        # These are deliberately high-confidence relational readings. They
        # create readable sustained states without pretending that transcript
        # keywords are full acoustic emotion recognition.
        if _contains_phrase(visitor_text, SUSPICION_PHRASES):
            return self._transition_from_observation(Emotion.SUSPICIOUS, cause="explicit suspicion phrase", confidence=0.96)
        elif _contains_phrase(visitor_text, VULNERABILITY_PHRASES):
            return self._transition_from_observation(Emotion.VULNERABLE, cause="explicit vulnerability phrase", confidence=0.98)
        elif _contains_phrase(visitor_text, STARTLE_PHRASES):
            return self._transition_from_observation(Emotion.STARTLED, cause="explicit startle phrase", confidence=0.96)
        elif self.emotion in {Emotion.WARY, Emotion.SUSPICIOUS, Emotion.HURT, Emotion.VULNERABLE} and kindness and not hostility:
            return self._transition_from_observation(Emotion.RELIEVED, cause="kindness after relational strain", confidence=0.88)
        elif self.hurt >= 3:
            return self._transition_from_observation(
                Emotion.WITHDRAWN if self.trust <= -2 else Emotion.ANGRY,
                cause="sustained relational harm",
                confidence=0.92,
            )
        elif hostility:
            return self._transition_from_observation(
                Emotion.HURT if prior_trust >= 0 else Emotion.WARY,
                cause="hostile visitor language",
                confidence=0.86,
            )
        elif _contains_phrase(value, DISAGREEMENT_PHRASES):
            return self._transition_from_observation(Emotion.WARY, cause="visitor disagrees", confidence=0.78)
        elif _contains_phrase(value, PERSONAL_DISCLOSURE_PHRASES):
            if len(self.turns) >= 1 and self.trust >= 1:
                return self._transition_from_observation(
                    Emotion.ENGAGED, cause="visitor shares a personal experience", confidence=0.82,
                )
            return self._transition_from_observation(
                Emotion.ATTENTIVE, cause="visitor offers a personal disclosure", confidence=0.80,
            )
        elif _question_like(value):
            return self._transition_from_observation(Emotion.ATTENTIVE, cause="visitor asks a considered question", confidence=0.74)
        elif kindness and first_encounter:
            return self._transition_from_observation(Emotion.HOPEFUL, cause="kindness at first encounter", confidence=0.84)
        elif kindness and len(self.turns) >= 2 and self.trust >= 3 and self.emotion in {Emotion.HOPEFUL, Emotion.ATTENTIVE, Emotion.ENGAGED}:
            return self._transition_from_observation(Emotion.ENGAGED, cause="earned trust", confidence=0.84)
        elif kindness:
            return self._transition_from_observation(Emotion.HOPEFUL, cause="visitor kindness", confidence=0.80)
        elif self.turns and self.trust < 0:
            return self._transition_from_observation(Emotion.WARY, cause="negative relationship signal", confidence=0.72)
        # Neutral exchanges preserve the current momentary emotion. They are
        # intentionally not promoted to ENGAGED merely because history exists.
        return self.emotion

    def remember(self, visitor_text: str, reply: str) -> None:
        self.turns.append((visitor_text, reply))
        if len(self.turns) > self.max_history:
            del self.turns[:-self.max_history]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "ambient": {
                "mood": self.ambient.mood.value,
                "source": self.ambient.source,
                "updated_at": self.ambient.updated_at,
            },
            "relationship": {
                "trust": self.relationship.trust,
                "hurt": self.relationship.hurt,
                "familiarity": self.relationship.familiarity,
                "last_encounter_at": self.relationship.last_encounter_at,
                "decay_applied_at": self.relationship.decay_applied_at,
                "opening_residue": self.relationship.opening_residue.value
                if self.relationship.opening_residue is not None
                else None,
                "residue_strength": self.relationship.residue_strength,
            },
            "momentary": {"emotion": self.emotion.value},
            "turns": list(self.turns),
            "durable_memories": list(self.durable_memories),
            "transitions": [
                {
                    "from_emotion": item.from_emotion.value,
                    "to_emotion": item.to_emotion.value,
                    "cause": item.cause,
                    "confidence": item.confidence,
                    "timestamp": item.timestamp,
                    "source": item.source,
                }
                for item in self.transitions
            ],
            "max_history": self.max_history,
            "max_transitions": self.max_transitions,
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        timestamp_factory: Callable[[], str] = _utc_timestamp,
    ) -> "ConversationState":
        """Load both the nested schema and the former flat state shape."""
        ambient_payload = payload.get("ambient", {})
        relationship_payload = payload.get("relationship", {})
        momentary_payload = payload.get("momentary", {})
        state = cls(
            ambient=AmbientMoodState(
                mood=AmbientMood(ambient_payload.get("mood", AmbientMood.DORMANT.value)),
                source=str(ambient_payload.get("source", "migration")),
                updated_at=ambient_payload.get("updated_at"),
            ),
            relationship=RelationshipState(
                trust=int(relationship_payload.get("trust", payload.get("trust", 0))),
                hurt=int(relationship_payload.get("hurt", payload.get("hurt", 0))),
                familiarity=int(relationship_payload.get("familiarity", 0)),
                last_encounter_at=relationship_payload.get("last_encounter_at"),
                decay_applied_at=relationship_payload.get("decay_applied_at"),
                opening_residue=(
                    Emotion(relationship_payload["opening_residue"])
                    if relationship_payload.get("opening_residue")
                    else None
                ),
                residue_strength=int(relationship_payload.get("residue_strength", 0)),
            ),
            momentary=MomentaryEmotionState(
                emotion=Emotion(momentary_payload.get("emotion", payload.get("emotion", Emotion.CURIOUS.value)))
            ),
            turns=[tuple(item) for item in payload.get("turns", [])],
            durable_memories=list(payload.get("durable_memories", [])),
            max_history=int(payload.get("max_history", 8)),
            max_transitions=int(payload.get("max_transitions", 64)),
            timestamp_factory=timestamp_factory,
        )
        for item in payload.get("transitions", []):
            state.transitions.append(
                EmotionTransition(
                    from_emotion=Emotion(item["from_emotion"]),
                    to_emotion=Emotion(item["to_emotion"]),
                    cause=str(item["cause"]),
                    confidence=float(item["confidence"]),
                    timestamp=str(item["timestamp"]),
                    source=str(item["source"]),
                )
            )
        state.transitions = state.transitions[-state.max_transitions:]
        return state
