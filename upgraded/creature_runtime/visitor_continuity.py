"""Pure VIS-01/VIS-02 memory-access policy preparation.

This does not recognize faces, issue tokens, read profiles, persist consent or
authorize Archive access. A future trusted adapter supplies validated token/local
match evidence. Camera track IDs and optional names are never identity proof.
"""
from dataclasses import dataclass
from enum import Enum
import math
import re

PROFILE_ID=re.compile(r'^[A-Za-z0-9_-]{1,64}$')


class Consent(str,Enum):
    UNKNOWN='unknown'
    GRANTED='granted'
    DECLINED='declined'


@dataclass(frozen=True)
class IdentityEvidence:
    participant_id:str
    source:str
    confidence:float
    verified:bool
    observed_at:float
    generation:int

    def __post_init__(self):
        if not isinstance(self.participant_id,str) or not PROFILE_ID.fullmatch(self.participant_id):
            raise ValueError('Bounded opaque participant id required')
        if self.source not in {'returning_token','local_visual'}:raise ValueError('Identity source required')
        if type(self.verified) is not bool:raise ValueError('Verified evidence flag required')
        if isinstance(self.confidence,bool) or not isinstance(self.confidence,(int,float)) or not math.isfinite(self.confidence) or not 0<=self.confidence<=1:
            raise ValueError('Finite confidence required')
        if isinstance(self.observed_at,bool) or not isinstance(self.observed_at,(int,float)) or not math.isfinite(self.observed_at):raise ValueError('Finite evidence time required')
        if type(self.generation) is not int or self.generation<1:raise ValueError('Encounter generation required')


@dataclass(frozen=True)
class MemoryAccess:
    participant_id:str|None
    may_recall:bool
    may_commit:bool
    reason:str
    anonymous_encounter:bool=True


def resolve_memory_access(*,consent:Consent,notice_seen:bool,evidence:IdentityEvidence|None,
                          now:float,generation:int,opted_out=frozenset(),revoked=frozenset(),
                          visual_threshold=.9,visual_lifetime=2.0):
    """Fail closed for uncertain identity; preserve the anonymous encounter.

    Visual thresholds/lifetimes are provisional policy knobs, not measured match
    accuracy. Token authentication must be performed by the future token adapter.
    No names, tracks, regions, images or biometric vectors enter this function.
    """
    deny=lambda reason:MemoryAccess(None,False,False,reason)
    if not isinstance(consent,Consent) or type(notice_seen) is not bool:raise ValueError('Typed consent and notice state required')
    if isinstance(now,bool) or not isinstance(now,(int,float)) or not math.isfinite(now) or type(generation) is not int or generation<1:raise ValueError('Encounter clock and generation required')
    for value in (visual_threshold,visual_lifetime):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Finite visual policy required')
    if not 0<=visual_threshold<=1 or not 0<visual_lifetime<=10:raise ValueError('Bounded visual policy required')
    if evidence is not None and not isinstance(evidence,IdentityEvidence):raise ValueError('Typed identity evidence required')
    for ids in (opted_out,revoked):
        if not isinstance(ids,(set,frozenset)) or any(not isinstance(key,str) or not PROFILE_ID.fullmatch(key) for key in ids):raise ValueError('Opaque identity sets required')
    if consent is Consent.DECLINED:return deny('memory_declined')
    if not notice_seen:return deny('notice_required')
    if consent is not Consent.GRANTED:return deny('consent_required')
    if evidence is None:return deny('identity_unresolved')
    if evidence.participant_id in opted_out:return deny('persistent_opt_out')
    if evidence.participant_id in revoked:return deny('identity_revoked')
    if evidence.generation!=generation:return deny('old_encounter')
    if not evidence.verified:return deny('unverified_identity')
    if evidence.observed_at>now:return deny('future_evidence')
    if evidence.source=='local_visual':
        if now-evidence.observed_at>=visual_lifetime:return deny('stale_visual_match')
        if evidence.confidence<visual_threshold:return deny('uncertain_visual_match')
    return MemoryAccess(evidence.participant_id,True,True,evidence.source,False)
