"""Attention selection from tracks; temporary track IDs are never identities."""
import time
import math


class AttentionTracker:
    def __init__(self, *, departure_grace=1.0, min_confidence=.45):
        self.departure_grace = departure_grace
        self.min_confidence = min_confidence
        self.reset()

    def reset(self):
        self.target = self.pending = None
        self.pending_since = self.seen = 0.0
        self.entered = {}

    def select(self, people, *, now=None, metric=False):
        now = time.monotonic() if now is None else now
        people = [p for p in people if isinstance(p.get('confidence'),(int,float)) and not isinstance(p['confidence'],bool) and math.isfinite(p['confidence']) and self.min_confidence <= p['confidence'] <= 1]
        visible = {p['track_id'] for p in people if not metric or p['distance_ft'] <= 15}
        self.entered = {k:v for k,v in self.entered.items() if k in visible}
        eligible = []
        for p in people:
            key = p['track_id']
            if metric and p['distance_ft'] > 15:continue
            self.entered.setdefault(key, now)
            # Only synthetic or explicitly measured depth may use metre/foot zones.
            if not metric or p['distance_ft'] <= 7 or (p['distance_ft'] <= 15 and now-self.entered[key] >= 2):
                eligible.append(p)
        current = next((p for p in eligible if p['track_id'] == self.target), None)
        area = lambda p: (p['bbox_xyxy'][2]-p['bbox_xyxy'][0])*(p['bbox_xyxy'][3]-p['bbox_xyxy'][1])
        best = (min(eligible, key=lambda p:p['distance_ft'], default=None) if metric
                else max(eligible, key=area, default=None))
        candidate = best if best and best != current else None
        if current:
            self.seen = now
            if candidate and (candidate['distance_ft'] > current['distance_ft']*.8 if metric else area(candidate)<area(current)*1.5):
                candidate = None
        if candidate:
            key = candidate['track_id']
            if self.pending != key:
                self.pending = key; self.pending_since = now
            if self.target is None or (now-self.pending_since >= 2 and (current or now-self.seen >= self.departure_grace)):
                self.target = key; self.seen = now; current = candidate; self.pending = None
        else:
            self.pending = None
        if not current and now-self.seen >= self.departure_grace and not candidate:
            self.target = None
        return {'attention_target':current, 'held_track_id':self.target,
                'pending_track_id':self.pending,
                'phase':'following' if current else 'searching' if self.target else 'neutral'}
