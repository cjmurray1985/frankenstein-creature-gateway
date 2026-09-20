from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import CreatureTurn
from .runtime import CreatureRuntime
from .session import ConversationSessionController


@dataclass
class CreatureSessionRunner:
    """Connect completed Creature turns to one archival session."""

    runtime: CreatureRuntime
    session: ConversationSessionController

    def handle_text(
        self, visitor_text: str, speaker_id: str, *, at: datetime | None = None
    ) -> CreatureTurn:
        self.session.begin_turn(at=at)
        try:
            turn = self.runtime.handle_text(visitor_text)
        except BaseException:
            self.session.abandon_turn(at=at)
            raise
        try:
            self.session.complete_turn(turn, speaker_id, at=at)
        except BaseException:
            # A successfully generated response that cannot be attributed must
            # not leave the lifecycle permanently marked in-flight.
            self.session.abandon_turn(at=at)
            raise
        return turn

