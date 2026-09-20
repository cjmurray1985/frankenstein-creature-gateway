from __future__ import annotations

from dataclasses import dataclass

from .models import Emotion, MotionIntent, ReplyPlan
from .state import ConversationState


LOCAL_REPLIES = {
    Emotion.CURIOUS: "You have come near, though many would turn away. Tell me—what did you hope to find here?",
    Emotion.HOPEFUL: "You speak with a kindness I have too seldom known. Stay a little; let me hear what you think of me.",
    Emotion.ENGAGED: "I have learned much by watching humanity from its margins. Your words make me wonder whether judgment may yet yield to understanding.",
    Emotion.WARY: "Take care. I have heard contempt concealed beneath gentler words, and I have learned to listen for it.",
    Emotion.HURT: "You name me monster before asking what suffering made of me. Is appearance the whole measure of a soul?",
    Emotion.ANGRY: "Do not mistake restraint for weakness. Cruelty taught me anger; I would rather you did not summon it again.",
    Emotion.WITHDRAWN: "Enough. I sought fellowship and found the old judgment waiting. Leave me to my silence.",
    Emotion.DORMANT: "...",
}


def motion_for(emotion: Emotion) -> MotionIntent:
    if emotion is Emotion.WITHDRAWN:
        return MotionIntent.WITHDRAW_GAZE
    if emotion in {Emotion.HURT, Emotion.ANGRY, Emotion.ENGAGED}:
        return MotionIntent.FACTORY_V1
    return MotionIntent.STILL_LISTENING


@dataclass(frozen=True)
class LoreGroundedLocalResponder:
    """Deterministic offline fallback shaped by the immutable creative north star."""

    def generate(self, visitor_text: str, state: ConversationState) -> ReplyPlan:
        emotion = state.observe(visitor_text)
        return ReplyPlan(LOCAL_REPLIES[emotion], emotion, motion_for(emotion))

