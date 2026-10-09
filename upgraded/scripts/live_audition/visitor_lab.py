"""Synthetic-only local rehearsal; no Pi, provider, durable profile or Archive writes."""
import math
import copy
import re
import time
import threading
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from creature_runtime.state import ConversationState
from creature_runtime.memory import MemoryFact, extract_explicit_facts
from creature_runtime.live_context import compose_live_context
from scripts.live_audition.attention import AttentionTracker


class VisitorLab:
    def __init__(self, *, clock=None, monotonic=None, record_id_factory=None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic or time.monotonic
        self.record_id_factory = record_id_factory or (lambda: uuid.uuid4().hex[:12])
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.tracker = AttentionTracker(departure_grace=4)
        self.now = self.clock()
        self.profiles = {}; self.facts = {}; self.retrievals = {}; self.current = None
        self.state = None; self.pending_facts = []; self.events = []

    def event(self, kind, detail):
        self.events.append({'at':self.now.isoformat(), 'kind':kind, 'detail':detail})
        self.events = self.events[-60:]

    def result(self):
        return {'synthetic':True, 'persistent':False, 'now':self.now.isoformat(),
                'visitor':self.current, 'encounter_open':self.state is not None,
                'state':self.state.to_dict() if self.state else None,
                'committed_state':copy.deepcopy(self.profiles.get(self.current)),
                'context':asdict(compose_live_context(self.state)) if self.state else None,
                'memories':[asdict(f) for f in self.facts.get(self.current, [])],
                'pending_facts':[asdict(f) for f in self.pending_facts],
                'retrievals':copy.deepcopy(self.retrievals.get(self.current,[])),
                'profiles':list(self.profiles), 'events':copy.deepcopy(self.events)}

    def request(self, body):
        with self.lock:
            action = body.get('action')
            if action == 'reset':
                self.reset(); return self.result()
            if action == 'reset_tracking':
                self.tracker.reset(); return {'synthetic':True,'tracking_reset':True}
            if action == 'observe':
                people=[]; faces=[]
                inputs=body.get('people',[])
                if not isinstance(inputs,list) or len(inputs)>3 or any(not isinstance(p,dict) for p in inputs):raise ValueError('People must be a list of synthetic tracks')
                keys=set()
                for item in inputs:
                    key=item.get('track_id')
                    if key in keys:raise ValueError('Duplicate synthetic track')
                    keys.add(key)
                    if key not in {'sim-a','sim-b','sim-c'}:raise ValueError('Synthetic track required')
                    vals=[item.get(k) for k in ['x','y','distance_ft']]
                    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):raise ValueError('Finite position required')
                    x,y,d=vals
                    if not (0<=x<=1 and 0<=y<=1 and 2<=d<=25):raise ValueError('Position outside rehearsal range')
                    w=min(.35,1.4/d);h=min(.65,3/d)
                    box=[max(0,x-w/2),max(0,y-h*.2),min(1,x+w/2),min(1,y+h*.8)]
                    people.append({'track_id':key,'confidence':1,'bbox_xyxy':box,'center_xy':[x,y],'distance_ft':d})
                    faces.append({'person_track_id':key,'bbox_xyxy':[max(0,x-.025),max(0,y-.025),min(1,x+.025),min(1,y+.025)],'quality':'synthetic','reasons':[],'coefficients':{}})
                if body.get('stale'):
                    self.tracker.reset()
                    selection={'attention_target':None,'held_track_id':None,'pending_track_id':None,'phase':'stale'}
                else:selection=self.tracker.select(people,now=self.monotonic(),metric=True)
                return {'schema_version':1,'mode':'synthetic_rehearsal','synthetic':True,'fresh':not bool(body.get('stale')),
                        'expires_after_ms':1000,'age_ms':0,'people':people,'facial_cues':faces,'objects':[],
                        'cloud_images':False,'actuation':False,**selection}
            if action == 'begin':
                if self.state is not None:raise ValueError('Complete or discard the open encounter first')
                key=body.get('visitor')
                if key not in {'lab-a','lab-b','lab-anonymous'}:raise ValueError('Use a synthetic visitor profile')
                self.current=key
                self.record_id='synthetic-'+self.record_id_factory()
                saved=self.profiles.get(key)
                self.state=ConversationState.from_dict(saved) if saved else ConversationState()
                self.state.turns=[];self.state.transitions=[];self.state.durable_memories=[f.text for f in self.facts.get(key,[])]
                self.state.timestamp_factory=lambda:self.now.isoformat()
                self.state.begin_encounter(at=self.now)
                self.pending_facts=[];self.event('begin',key)
                facts=self.facts.get(key,[])
                if facts:
                    recall={'encounter_id':self.record_id,'source_record_ids':sorted({f.source_record_id for f in facts}),'fact_count':len(facts),'at':self.now.isoformat()}
                    self.retrievals.setdefault(key,[]).append(recall);self.retrievals[key]=self.retrievals[key][-100:]
                    self.event('recall',recall)
            elif action == 'turn':
                if self.state is None:raise ValueError('Begin an encounter first')
                text=body.get('text','')
                if not isinstance(text,str) or not text.strip() or len(text)>500:raise ValueError('Enter 1–500 characters')
                self.state.observe(text);self.state.remember(text,'[Rehearsal: no generated reply]')
                self.pending_facts.extend(MemoryFact(f.text,f.source_record_id,f.confidence,self.now.isoformat()) for f in extract_explicit_facts(text,self.record_id))
                self.pending_facts=self.pending_facts[-24:]
                self.event('turn',self.state.emotion.value)
            elif action == 'complete':
                if self.state is None:raise ValueError('No open encounter')
                self.state.complete_encounter(at=self.now)
                if self.current!='lab-anonymous':
                    self.profiles[self.current]=self.state.to_dict()
                    facts=self.facts.setdefault(self.current,[])
                    for fact in self.pending_facts:
                        if not any(f.text.casefold()==fact.text.casefold() for f in facts):facts.append(fact)
                    self.facts[self.current]=facts[-24:]
                self.event('complete',self.current);self.state=None;self.pending_facts=[]
            elif action == 'discard':
                if self.state is None:raise ValueError('No open encounter')
                self.event('discard',self.current);self.state=None;self.pending_facts=[]
            elif action == 'advance':
                if self.state is not None:raise ValueError('Complete or discard before advancing time')
                days=body.get('days',14)
                if not isinstance(days,int) or isinstance(days,bool) or not 1<=days<=365:raise ValueError('Advance 1–365 days')
                self.now+=timedelta(days=days);self.event('time',f'+{days} days')
            elif action == 'forget':
                if self.state is not None:raise ValueError('Complete or discard before forgetting')
                key=body.get('visitor',self.current)
                if key not in {'lab-a','lab-b','lab-anonymous'}:raise ValueError('Select a synthetic profile')
                self.profiles.pop(key,None);self.facts.pop(key,None);self.retrievals.pop(key,None);self.current=key;self.event('forget',key)
            elif action != 'status':raise ValueError('Unknown rehearsal action')
            return self.result()


class VisitorLabSessions:
    """Bounded, process-only rehearsal isolation between browser pages."""
    def __init__(self, *, monotonic=None, max_sessions=32, idle_seconds=7200):
        self.monotonic=monotonic or time.monotonic
        self.max_sessions=max_sessions;self.idle_seconds=idle_seconds
        self.sessions={};self.lock=threading.Lock()

    def request(self, body):
        key=body.get('lab_session')
        if not isinstance(key,str) or not re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',key):
            raise ValueError('Valid rehearsal session required')
        with self.lock:
            now=self.monotonic()
            self.sessions={k:v for k,v in self.sessions.items() if now-v[1]<self.idle_seconds}
            if key not in self.sessions:
                if len(self.sessions)>=self.max_sessions:raise ValueError('Close another rehearsal page before opening a new session')
                self.sessions[key]=(VisitorLab(),now)
            lab,_=self.sessions[key];self.sessions[key]=(lab,now)
        return lab.request(body)
