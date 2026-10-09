"""Loopback-only, metadata-only encounter perception adapter. No motion/cloud calls."""
import json
import math
import threading
import time
import urllib.request
from scripts.live_audition.attention import AttentionTracker


class LocalVision:
    def __init__(self):
        self.lock=threading.Lock();self.tracker=AttentionTracker()

    def read(self):
        begin=time.monotonic()
        try:
            with urllib.request.urlopen('http://localhost:8770/status',timeout=.6) as response:
                body=response.read(512001)
            if len(body)>512000:raise ValueError('Observation exceeds bound')
            value=json.loads(body);o=value.get('observation') or {}
            age=float(value.get('age_ms') or 0)+(time.monotonic()-begin)*1000
            if not value.get('fresh') or not math.isfinite(age) or age>=1000:
                return self.unavailable('Camera observation stale or unavailable.')
            people=[]
            for item in o.get('objects',[])[:100]:
                if item.get('label')!='person':continue
                box=item.get('bbox_xyxy');confidence=item.get('confidence',0)
                if not isinstance(box,list) or len(box)!=4 or not all(isinstance(v,(float,int)) and math.isfinite(v) and 0<=v<=1 for v in box):continue
                if box[2]<=box[0] or box[3]<=box[1] or not isinstance(confidence,(float,int)) or not math.isfinite(confidence):continue
                people.append({'track_id':str(item.get('track_id',''))[:64],'confidence':confidence,'bbox_xyxy':box,'center_xy':[(box[0]+box[2])/2,(box[1]+box[3])/2]})
            with self.lock:
                selection=self.tracker.select(people)
                current=selection['attention_target'];selected_id=selection['held_track_id']
            cues=[]
            for f in o.get('faces',[])[:3]:
                coefficients={k:v for k,v in f.get('visible_coefficients',{}).items() if k in {'eyeBlinkLeft','eyeBlinkRight','jawOpen','mouthSmileLeft','mouthSmileRight','browInnerUp','browDownLeft','browDownRight'} and isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1}
                q=f.get('quality',{})
                cues.append({'person_track_id':f.get('person_track_id'),'bbox_xyxy':f.get('bbox_xyxy'),'coefficients':coefficients,'quality':q.get('status','uncertain'),'reasons':[str(v)[:100] for v in q.get('reasons',[])[:10]],'face_width_px':q.get('face_width_px')})
            return {'schema_version':1,'mode':'observation_only','fresh':True,'source_frame_id':o.get('frame_id'),'observed_at':o.get('observed_at'),
                'age_ms':round(age),'expires_after_ms':max(0,round(1000-age)),'people':people[:10],'attention_target':current,
                'held_track_id':selected_id,'facial_cues':cues,'objects':[{'label':str(v.get('label',''))[:64],'confidence':v.get('confidence')} for v in o.get('objects',[])[:30] if v.get('label')!='person'],
                'focus_recovering':bool(o.get('face_focus',{}).get('recovery_active')),'cloud_images':False,'actuation':False,
                'interpretation':'Largest apparent person with 2-second switch hysteresis; not nearest distance, identity, emotion or calibrated gaze.'}
        except Exception as exc:return self.unavailable('Local Vision unavailable ('+type(exc).__name__+').')

    def unavailable(self,reason):
        with self.lock:self.tracker.reset()
        return {'schema_version':1,'mode':'observation_only','fresh':False,'expires_after_ms':0,'people':[],'attention_target':None,'facial_cues':[],'objects':[], 'reason':reason,'cloud_images':False,'actuation':False}
