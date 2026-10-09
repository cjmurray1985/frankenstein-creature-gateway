// Semantic normalized targets; these are not pulse widths. The opt-in local
// bridge maps them through its recorded rest/range table. PCA labels below are
// the current retrofit wiring, not the original factory animation signal IDs.
export const HEAD_CHANNELS = Object.freeze({
  CH1: {pca:'PWM0', role:'Neck flexion/extension', confirmed:true},
  CH2: {pca:'PWM3', role:'Neck rotation', confirmed:true},
  CH3: {pca:'PWM5', role:'Neck lateral flexion', confirmed:true},
  CH4: {pca:'PWM7', role:'Right eye vertical · up/down', confirmed:true},
  CH5: {pca:'PWM8', role:'Left eye vertical · up/down', confirmed:true},
  CH6: {pca:'PWM11', role:'Left eye horizontal · left/right', confirmed:true},
  CH7: {pca:'PWM13', role:'Right eye horizontal · left/right', confirmed:true},
  CH8: {pca:'PWM15', role:'Linked eyelids · open/close', confirmed:true},
});
export const AUX_SIGNALS = Object.freeze({
  LED_BOLTS: {role:'Left/right neck-bolt LEDs · shared signal', confirmed:true},
});
export const RIG = Object.freeze({
  CH1: {label:HEAD_CHANNELS.CH1.role, evidence:'confirmed mechanism; travel uncalibrated'},
  CH2: {label:HEAD_CHANNELS.CH2.role, evidence:'confirmed mechanism; travel uncalibrated'},
  CH3: {label:HEAD_CHANNELS.CH3.role, evidence:'confirmed mechanism; travel uncalibrated'},
  CH4: {label:HEAD_CHANNELS.CH4.role, evidence:'identified; electrical envelope measured'},
  CH5: {label:HEAD_CHANNELS.CH5.role, evidence:'identified; travel uncalibrated'},
  CH6: {label:HEAD_CHANNELS.CH6.role, evidence:'identified; travel uncalibrated'},
  CH7: {label:HEAD_CHANNELS.CH7.role, evidence:'identified; travel uncalibrated'},
  CH8: {label:HEAD_CHANNELS.CH8.role, evidence:'identified; travel uncalibrated'},
  M1: {label:'Mouth opening', evidence:'continuous face skin; motor linkage, no detached chin'},
  LED_BOLTS: {label:AUX_SIGNALS.LED_BOLTS.role, evidence:'left/right neck bolts share one signal; source channel not specified'},
});
export const DIRECTIONS = Object.freeze({
  // These are expressive targets, not hardware calibration values. The
  // small head offsets and accent terms keep an emotion readable without
  // turning every spoken syllable into a servo gesture.
  dormant:{gazeX:0,gazeY:-.25,lids:.88,neckFlex:.22,neckRotation:0,neckLateral:0,led:0,jaw:0.86,gazeRate:.42,neckRate:.13,accentFlex:0,accentRotation:0,accentLateral:0,sway:.004,ledPulse:0},
  curious:{gazeX:0,gazeY:0,lids:.38,neckFlex:0,neckRotation:0,neckLateral:0,led:0,jaw:1,gazeRate:.68,neckRate:.22,accentFlex:-.018,accentRotation:.012,accentLateral:.006,sway:.009,ledPulse:0,eyeAsymX:0,eyeAsymY:0},
  // Attention is a held, focused look with the head inclining toward the visitor.
  // Keep the body quiet so the direct gaze reads before any conversational cue.
  attentive:{gazeX:0,gazeY:.02,lids:.43,neckFlex:-.20,neckRotation:0,neckLateral:0,led:.12,jaw:1.01,gazeRate:.48,neckRate:.20,accentFlex:-.055,accentRotation:.012,accentLateral:.004,sway:.002,ledPulse:.04,eyeAsymX:0,eyeAsymY:0},
  hopeful:{gazeX:0,gazeY:.07,lids:.20,neckFlex:-.18,neckRotation:0,neckLateral:0,led:.28,jaw:1.02,gazeRate:.72,neckRate:.23,accentFlex:-.045,accentRotation:.025,accentLateral:.012,sway:.014,ledPulse:.10},
  // Engagement is direct attention: lids narrow, the head leans in, and the
  // eyes make a slow human scan instead of freezing on one point.
  engaged:{gazeX:.055,gazeY:.08,lids:.46,neckFlex:-.12,neckRotation:.075,neckLateral:.035,led:.38,jaw:1.04,gazeRate:.82,neckRate:.28,accentFlex:-.075,accentRotation:.05,accentLateral:.025,sway:.014,ledPulse:.12},
  wary:{gazeX:.25,gazeY:-.08,lids:.50,neckFlex:.16,neckRotation:.065,neckLateral:-.09,led:.08,jaw:.94,gazeRate:.78,neckRate:.20,accentFlex:.025,accentRotation:.06,accentLateral:-.025,sway:.006,ledPulse:.035,eyeAsymX:0,eyeAsymY:0},
  // Suspicion holds a paired side glance. Offset pupils read as misaligned
  // mechanics; suspicion comes from gaze direction, narrow lids and head turn.
  suspicious:{gazeX:.38,gazeY:-.06,lids:.50,neckFlex:.20,neckRotation:.13,neckLateral:-.13,led:.06,jaw:.91,gazeRate:.84,neckRate:.19,accentFlex:.03,accentRotation:.075,accentLateral:-.035,sway:.002,ledPulse:.02,eyeAsymX:0,eyeAsymY:0},
  startled:{gazeX:0,gazeY:.20,lids:.05,neckFlex:-.22,neckRotation:-.04,neckLateral:0,led:.72,jaw:1.05,gazeRate:1.5,neckRate:.52,accentFlex:-.12,accentRotation:.03,accentLateral:0,sway:.012,ledPulse:.24,eyeAsymX:0,eyeAsymY:0},
  hurt:{gazeX:-.30,gazeY:-.32,lids:.43,neckFlex:.28,neckRotation:0,neckLateral:.11,led:.03,jaw:.92,gazeRate:.52,neckRate:.17,accentFlex:.018,accentRotation:-.025,accentLateral:.018,sway:.004,ledPulse:.015,eyeAsymX:0,eyeAsymY:0},
  vulnerable:{gazeX:-.10,gazeY:.27,lids:.40,neckFlex:-.16,neckRotation:-.045,neckLateral:.12,led:.10,jaw:.96,gazeRate:.50,neckRate:.17,accentFlex:-.03,accentRotation:-.03,accentLateral:.03,sway:.003,ledPulse:.025,eyeAsymX:0,eyeAsymY:0},
  angry:{gazeX:0,gazeY:.04,lids:.49,neckFlex:-.14,neckRotation:0,neckLateral:0,led:.58,jaw:1.08,gazeRate:1.12,neckRate:.34,accentFlex:-.11,accentRotation:.065,accentLateral:.03,sway:.003,ledPulse:.18,eyeAsymX:0,eyeAsymY:0},
  // Relief visibly releases the attentive lean: eyes open, head settles back,
  // then the short relief cue supplies a soft nod rather than a fixed grimace.
  relieved:{gazeX:0,gazeY:.02,lids:.20,neckFlex:.12,neckRotation:-.06,neckLateral:.035,led:.24,jaw:1.01,gazeRate:.58,neckRate:.26,accentFlex:.02,accentRotation:-.035,accentLateral:.018,sway:.014,ledPulse:.08,eyeAsymX:0,eyeAsymY:0},
  withdrawn:{gazeX:-.42,gazeY:-.38,lids:.67,neckFlex:.38,neckRotation:0,neckLateral:.15,led:0,jaw:.82,gazeRate:.42,neckRate:.15,accentFlex:.006,accentRotation:-.015,accentLateral:.008,sway:0,ledPulse:0,eyeAsymX:0,eyeAsymY:0},
});
export const EMOTION_PROFILES=DIRECTIONS;
export const CUES=Object.freeze({
  none:{duration:0},
  // Momentary conversational gestures. Values are normalized preview
  // offsets, not calibrated servo travel or PWM.
  think:{duration:1.40,gazeY:.20,flex:-.045,lateral:.025,lids:-.06},
  agree:{duration:1.25,nod:.13,flex:-.02,lids:-.035},
  disagree:{duration:1.40,shake:.14,lateral:.012,lids:.035},
  listening:{duration:1.45,gazeY:.035,flex:-.065,lids:-.025},
  surprise:{duration:1.00,gazeY:.12,flex:-.11,lids:-.38,led:.16},
  startle:{duration:1.00,gazeY:.12,flex:-.11,lids:-.38,led:.26},
  suspicion:{duration:1.40,gazeX:.16,rotation:.10,lateral:-.045,lids:.08},
  repair:{duration:1.35,nod:.10,flex:-.018,lids:-.04,gazeY:.035},
  plead:{duration:1.45,gazeY:.13,flex:-.06,lateral:.035,lids:-.06,led:.05},
  relief:{duration:1.55,nod:.14,flex:.045,lateral:.035,lids:-.05,gazeY:-.10,led:.08},
  withdraw:{duration:1.45,gazeX:.16,rotation:.18,flex:.06,lids:.10},
});
export const clamp = (v,lo=0,hi=1)=>Math.max(lo,Math.min(hi,v));
// Cinematic staging assumptions, not dimensions measured from the KIRI scan.
export const ENCOUNTER_STAGE=Object.freeze({creatureFeet:8,visitorFeet:71/12,eyeInsetFeet:4/12,distanceFeet:5,headCenterFeet:7,waistFeet:4.2,unitsPerFoot:3.7/2});
export function entrancePose(seconds,reduced=false){
  // Begin the hinge on the first rendered frame. The prior 450ms dead hold
  // made a successfully loaded mobile scene appear stalled.
  const t=reduced?1:clamp(seconds/4.6),progress=t*t*t*(t*(6*t-15)+10);
  // A readable low-key silhouette is present immediately and strengthens as
  // the body rises. Full portrait light still waits until after the sit-up.
  const silhouette=reduced?1:clamp(seconds/2.8);
  const r=reduced?1:clamp((seconds-5.7)/2.8);
  const reveal=reduced?1:.22+.12*silhouette*silhouette*(3-2*silhouette)+.66*r*r*(3-2*r);
  // Keep the lids shut through the sit-up. Once upright, snap them open for
  // a brief startle, then ease back to the normal resting opening.
  const upright=progress>=1;
  const jump=reduced?1:clamp((seconds-8.5)/.24);
  const settleEyes=reduced?1:clamp((seconds-8.74)/1.1);
  const eyeOpen=reduced?1:upright?(jump<1?1.85*jump:1.85-(.85*settleEyes*settleEyes*(3-2*settleEyes))):0;
  const settle=clamp((progress-.65)/.35);
  // The visitor is on +Z. Reclining toward -Z places the head behind the
  // hips, face upward; rising then travels upward AND toward the visitor.
  // Keep the camera fixed and acquire the downward gaze only near upright.
  return {progress,reveal,lean:-(1-progress)*Math.PI/2,headPitch:.28*settle*settle*(3-2*settle),framing:1,eyeOpen,complete:t===1&&r===1};
}
export function approach(value,target,speed,dt) {
  return value+clamp(target-value,-speed*dt,speed*dt);
}
export function audioEnvelope(samples,rate=44100) {
  const hop=Math.max(1,Math.round(rate*.01)), out=[];
  for(let i=0;i<samples.length;i+=hop) {
    let energy=0,peak=0;
    const end=Math.min(i+hop,samples.length);
    for(let j=i;j<end;j++){energy+=samples[j]*samples[j];peak=Math.max(peak,Math.abs(samples[j]));}
    const rms=Math.sqrt(energy/(end-i));
    // The physical mouth has one opening axis; no invented phoneme blendshapes.
    out.push({time:i/rate,open:clamp((rms-.009)*7.5),rms,peak});
  }
  return out;
}
export class AudioMotion {
  constructor(){this.clear();}
  clear(){this.segments=[];}
  enqueue(samples,rate,start,emotion='curious'){
    this.segments.push({start,end:start+samples.length/rate,envelope:audioEnvelope(samples,rate),emotion});
  }
  at(time){
    while(this.segments.length&&this.segments[0].end<=time)this.segments.shift();
    const s=this.segments[0];
    if(!s||time<s.start)return {open:0,rms:0,speaking:false};
    const e=s.envelope[Math.min(s.envelope.length-1,Math.floor((time-s.start)/.01))];
    return {...e,emotion:s.emotion,speaking:true};
  }
}
export class MechanicalPose {
  constructor(){this.reset();}
  reset(){const expressive=this.expressive===true;this.jaw=0;this.x=0;this.y=0;this.lids=DIRECTIONS.curious.lids;this.neckFlex=0;this.neckRotation=0;this.neckLateral=0;this.silence=10;this.speechAge=10;this.speakingAge=10;this.wasSpeaking=false;this.emotionAge=10;this.emotionName='curious';this.cueName='none';this.cueAge=999;this.lastOpen=0;this.lastAccent=-10;this.accent=0;this.clock=0;this.lastCues=new Map();this.expressive=expressive;}
  setExpressive(value){this.expressive=Boolean(value);}
  setCue(value){if(value&&CUES[value]&&value!==this.cueName&&this.clock-(this.lastCues.get(value)??-Infinity)>=3){this.cueName=value;this.cueAge=0;this.lastCues.set(value,this.clock);}}
  step(input,emotion,dt,blink=0){
    dt=clamp(dt,0,.05);
    const d=DIRECTIONS[emotion]||DIRECTIONS.curious;
    if(input.cue)this.setCue(input.cue);
    const cue=CUES[this.cueName]||CUES.none;
    if(cue.duration){this.cueAge+=dt;if(this.cueAge>=cue.duration){this.cueName='none';this.cueAge=999;}}
    const cueActive=cue.duration&&this.cueAge<cue.duration;
    const cueT=cueActive?this.cueAge/cue.duration:0;
    const cueEnvelope=cueActive?Math.sin(Math.PI*cueT):0;
    const cueOscillation=cueActive?Math.sin(Math.PI*2*(cue.nod?1.0:cue.shake?.85:1)*cueT)*cueEnvelope:0;
    if(emotion!==this.emotionName){this.emotionName=emotion;this.emotionAge=0;}
    this.clock+=dt;this.emotionAge+=dt;
    const open=clamp(Number(input.open)||0),speaking=Boolean(input.speaking),rms=Number(input.rms)||0;
    if(speaking){if(!this.wasSpeaking||this.silence>.6){this.speechAge=0;this.speakingAge=0;}this.silence=0;this.speakingAge+=dt;}else{this.silence+=dt;this.speakingAge=10;}
    this.wasSpeaking=speaking;
    // One restrained physical emphasis per breath-sized phrase. The trigger
    // is deliberately based on the audio envelope's rising edge, not every
    // frame, so the neck never becomes a syllable-by-syllable metronome.
    if(speaking&&rms>.075&&open>.48&&this.lastOpen<=.48&&this.clock-this.lastAccent>.72){this.accent=1;this.lastAccent=this.clock;}
    this.accent=approach(this.accent,0,2.6,dt);this.lastOpen=open;
    // Provisional visual slew limits, deliberately unrelated to unmeasured hardware speed.
    // Expressive mode exaggerates semantic motion around the curious baseline,
    // keeping the same normalized bounds while making emotion legible at a
    // glance. Audio-driven jaw motion remains unchanged.
    const emotionGain=this.expressive?1.7:1;
    const cueGain=this.expressive?2.1:1;
    const swayGain=this.expressive?1.45:1;
    const scanRate=emotion==='engaged'?1.15:emotion==='attentive'?.32:emotion==='curious'?.72:emotion==='wary'?1.45:emotion==='suspicious'?.28:emotion==='hopeful'?.55:0;
    const scanAmount=this.expressive?(emotion==='engaged'?.12:emotion==='attentive'?.018:emotion==='curious'?.055:emotion==='wary'?.045:emotion==='suspicious'?.012:emotion==='hopeful'?.025:0):0;
    const socialScan=scanAmount?Math.sin(this.clock*scanRate)*scanAmount:0;
    const gazeX=d.gazeX*emotionGain+socialScan+(cue.gazeX||0)*cueGain*cueEnvelope;
    const gazeY=d.gazeY*emotionGain+(emotion==='engaged'&&this.expressive?Math.sin(this.clock*.63)*.022:0)+(cue.gazeY||0)*cueGain*cueEnvelope;
    const lidGain=this.expressive?1.2:1;
    const lidCeiling=emotion==='dormant'?.88:emotion==='withdrawn'?.73:.58;
    const lidTarget=clamp(DIRECTIONS.curious.lids+(d.lids-DIRECTIONS.curious.lids)*lidGain+(cue.lids||0)*cueGain*cueEnvelope,0,lidCeiling);
    this.jaw=approach(this.jaw,clamp(open*d.jaw),open*d.jaw>this.jaw?5:7,dt);
    this.x=approach(this.x,gazeX,d.gazeRate,dt);
    this.y=approach(this.y,gazeY,d.gazeRate*.78,dt);
    this.lids=approach(this.lids,Math.max(lidTarget,blink),blink?8:2.8,dt);
    const breathSway=speaking?Math.sin(this.speakingAge*2.1)*d.sway*swayGain:0;
    this.speechAge+=dt;
    const nod=this.speechAge<1.4?Math.sin(this.speechAge/1.4*Math.PI)*.10:0;
    // Gaze acquires first; the neck follows with slower, restrained movement.
    const flexTarget=d.neckFlex*emotionGain+nod+breathSway+d.accentFlex*this.accent*emotionGain+(cue.flex||0)*cueGain*cueEnvelope+(cue.nod||0)*cueGain*cueOscillation;
    const rotationTarget=this.x+d.neckRotation*emotionGain+breathSway*.35+d.accentRotation*this.accent*emotionGain+(cue.rotation||0)*cueGain*cueEnvelope+(cue.shake||0)*cueGain*cueOscillation;
    const lateralTarget=d.neckLateral*emotionGain+breathSway*.55+d.accentLateral*this.accent*emotionGain+(cue.lateral||0)*cueGain*cueEnvelope;
    this.neckRotation=approach(this.neckRotation,rotationTarget,d.neckRate,dt);
    this.neckFlex=approach(this.neckFlex,flexTarget,d.neckRate,dt);
    this.neckLateral=approach(this.neckLateral,lateralTarget,d.neckRate,dt);
    const ledPulse=speaking?d.ledPulse*(.5+.5*Math.sin(this.clock*2.2))*emotionGain:0;
    const eyeAsymX=(d.eyeAsymX||0)*emotionGain,eyeAsymY=(d.eyeAsymY||0)*emotionGain;
    return {CH1:clamp(this.neckFlex,-1,1),CH2:clamp(this.neckRotation,-1,1),CH3:clamp(this.neckLateral,-1,1),CH4:clamp(this.y+eyeAsymY,-1,1),CH5:clamp(this.y-eyeAsymY,-1,1),CH6:clamp(this.x-eyeAsymX,-1,1),CH7:clamp(this.x+eyeAsymX,-1,1),CH8:clamp(this.lids),M1:this.jaw,LED_BOLTS:clamp(d.led*emotionGain+ledPulse+(cue.led||0)*cueGain*cueEnvelope)};
  }
}

// Command-space twin of hardware_panel/worker.py::_servo_loop. This models
// commanded pulses, not measured shafts. Keep coefficients in parity with Pi.
export class ServoPreviewFollower {
  constructor(specs){this.specs=specs;this.reset();}
  reset(){this.current=Object.fromEntries(Object.entries(this.specs).map(([id,s])=>[id,s[1]]));this.targets={...this.current};}
  // Python round() uses ties to even; reproduce it for target and write pulses.
  static round(value){const floor=Math.floor(value),fraction=value-floor;return fraction===.5?(floor%2===0?floor:floor+1):Math.round(value);}
  target(p){for(const [id,s] of Object.entries(this.specs)){const value=id==='CH8'?1-2*p[id]:p[id];this.targets[id]=ServoPreviewFollower.round(s[1]+value*(value>=0?s[2]-s[1]:s[1]-s[0]));}}
  tick(dt){
    dt=Math.min(.04,Math.max(0,dt));
    const eyeSettled=['CH4','CH5','CH6','CH7'].every(id=>Math.abs(this.targets[id]-this.current[id])<=.5);
    for(const id of Object.keys(this.specs)){
      const target=this.targets[id],current=this.current[id];
      const tau=Number(id.slice(2))<=3?.160:id==='CH8'?(target>current?.080:.035):.045;
      const settled=['CH4','CH5','CH6','CH7'].includes(id)?eyeSettled:Math.abs(target-current)<=.5;
      this.current[id]=settled?target:current+(-Math.expm1(-dt/tau))*(target-current);
    }
  }
  pulses(){return Object.fromEntries(Object.entries(this.current).map(([id,value])=>[id,ServoPreviewFollower.round(value)]));}
  pose(p){const rendered={...p},pulses=this.pulses();for(const [id,s] of Object.entries(this.specs)){const delta=pulses[id]-s[1],value=delta/(delta>=0?s[2]-s[1]:s[1]-s[0]);rendered[id]=id==='CH8'?(1-value)/2:value;}return rendered;}
}
