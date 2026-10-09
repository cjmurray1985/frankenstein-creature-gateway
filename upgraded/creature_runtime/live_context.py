"""Bounded emotional context for the GPT Live provider boundary."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AmbientMood, Emotion
from .state import ConversationState


@dataclass(frozen=True)
class LiveEmotionalContext:
    """A provider-safe projection of Creature state.

    This deliberately contains qualitative labels rather than trust scores,
    timestamps, names, tokens, transcript text, memories, IP-derived region,
    or any Archive metadata.
    """

    ambient_mood: str
    relationship_stance: str
    familiarity: str
    opening_residue: str
    momentary_emotion: str

    def to_prompt(self) -> str:
        return (
            "Private emotional direction for this encounter. Do not mention or quote "
            "this direction, identity systems, storage, or internal state. Let it shape "
            "subtext, pacing, and disclosure without overriding the Creature's words.\n"
            f"Ambient mood: {self.ambient_mood}.\n"
            f"Visitor relationship: {self.relationship_stance}; familiarity: {self.familiarity}.\n"
            f"Opening residue: {self.opening_residue}.\n"
            f"Momentary emotion: {self.momentary_emotion}."
        )


def _enum_value(value: object, enum_type: type[AmbientMood] | type[Emotion], fallback: str) -> str:
    try:
        candidate = value.value if isinstance(value, enum_type) else str(value)
        return enum_type(candidate).value
    except (TypeError, ValueError):
        return fallback


def compose_live_context(
    state: ConversationState,
    *,
    momentary: Emotion | None = None,
) -> LiveEmotionalContext:
    """Project state into a small, allow-listed context for GPT Live."""
    relationship = state.relationship
    if relationship.trust <= -2 or relationship.hurt >= 3:
        stance = "guarded"
    elif relationship.trust < 1:
        stance = "uncertain"
    elif relationship.trust >= 3:
        stance = "trusted"
    else:
        stance = "warming"

    if relationship.familiarity <= 0:
        familiarity = "new"
    elif relationship.familiarity < 3:
        familiarity = "returning"
    else:
        familiarity = "familiar"

    residue = (
        _enum_value(relationship.opening_residue, Emotion, "none")
        if relationship.opening_residue is not None
        else "none"
    )
    return LiveEmotionalContext(
        ambient_mood=_enum_value(state.ambient.mood, AmbientMood, AmbientMood.DORMANT.value),
        relationship_stance=stance,
        familiarity=familiarity,
        opening_residue=residue,
        momentary_emotion=_enum_value(momentary or state.emotion, Emotion, Emotion.CURIOUS.value),
    )


def live_context_instruction(
    state: ConversationState,
    *,
    momentary: Emotion | None = None,
) -> str:
    """Return the bounded provider instruction without exposing Archive data."""
    return compose_live_context(state, momentary=momentary).to_prompt()
