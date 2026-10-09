// Semantic ownership of gaze channels. Safety/calibration stay above performance.
// Seconds are from one monotonic clock; no wall clock or random timing.
export const REACTION_TIMING=Object.freeze({
  startled:{hold:1.5,cooldown:4},angry:{hold:2.2,cooldown:5},withdrawn:{hold:2.5,cooldown:5},
  suspicious:{hold:1.2,cooldown:3.5},hurt:{hold:2,cooldown:4},
  vulnerable:{hold:2.2,cooldown:4},relieved:{hold:2,cooldown:4},
});
export const GLANCE_CUES=new Set(['think','agree','disagree','listening','surprise','startle','suspicion','repair','plead','relief','withdraw']);
export class PerformanceArbiter {
  constructor(){this.reset();}
  reset(){this.emotion=null;this.cue='none';this.holdUntil=-Infinity;this.holdEmotion=null;this.lastReaction=new Map();this.lastCue=new Map();this.cueUntil=-Infinity;this.wasSpeaking=false;this.settleUntil=-Infinity;this.events=[];}
  note(now,kind,value){this.events.push({at:now,kind,value});this.events=this.events.slice(-60);}
  step({now,emotion='curious',cue='none',cueRemaining=0,speaking=false,tracking=false,study=false,safety=false}){
    if(!Number.isFinite(now))throw new TypeError('Finite performance time required');
    if(emotion!==this.emotion){
      const timing=REACTION_TIMING[emotion];
      if(timing&&now-(this.lastReaction.get(emotion)??-Infinity)>=timing.cooldown){
        this.holdUntil=now+timing.hold;this.holdEmotion=emotion;this.lastReaction.set(emotion,now);this.note(now,'reaction',emotion);
      }
      this.emotion=emotion;
    }
    if(cue!==this.cue){
      if(GLANCE_CUES.has(cue)&&now-(this.lastCue.get(cue)??-Infinity)>=3){
        this.cueUntil=now+Math.min(1.6,Math.max(0,cueRemaining));this.lastCue.set(cue,now);this.note(now,'cue',cue);
      }
      this.cue=cue;
    }
    if(this.wasSpeaking&&!speaking)this.settleUntil=now+.45;
    this.wasSpeaking=speaking;
    const beat=speaking?'during-speech':now<this.settleUntil?'settling':now<this.holdUntil||now<this.cueUntil?'pre-speech':'listening';
    let owner=safety?'safety':study?'study':now<this.holdUntil?'emotion':now<this.cueUntil?'conversation':tracking?'visitor':'rest';
    return {owner,beat,emotion:now<this.holdUntil?this.holdEmotion:emotion,gazeAllowed:owner==='visitor'||owner==='rest',reaction:now<this.holdUntil?this.holdEmotion:null,
            holdRemaining:Math.max(0,this.holdUntil-now),cueRemaining:Math.max(0,this.cueUntil-now)};
  }
}
