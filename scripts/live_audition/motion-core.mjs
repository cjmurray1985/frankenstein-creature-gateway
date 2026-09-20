// Normalized preview travel only: these values MUST NOT be converted to PWM.
// CH4–CH8 assignments and M1 mouth motor come from the preserved Phase 2 wiring record.
export const RIG = Object.freeze({
  CH4: {label:'Right eye · vertical', evidence:'identified; electrical envelope measured'},
  CH5: {label:'Left eye · vertical', evidence:'identified; travel uncalibrated'},
  CH6: {label:'Left eye · horizontal', evidence:'identified; travel uncalibrated'},
  CH7: {label:'Right eye · horizontal', evidence:'identified; travel uncalibrated'},
  CH8: {label:'Coupled eyelids', evidence:'identified; travel uncalibrated'},
  M1: {label:'Mouth opening', evidence:'continuous face skin; motor linkage, no detached chin'},
  NECK_SIDE: {label:'Neck · side to side', evidence:'user-confirmed and visible in full-cycle video; channel assignment unresolved'},
  NECK_FB: {label:'Neck · front/back', evidence:'user-confirmed and visible in full-cycle video; channel assignment unresolved'},
});
export const DIRECTIONS = Object.freeze({
  dormant:{gazeX:0,gazeY:-.25,lids:.82},
  curious:{gazeX:0,gazeY:0,lids:.58},
  hopeful:{gazeX:0,gazeY:.12,lids:.50},
  engaged:{gazeX:0,gazeY:.05,lids:.55},
  wary:{gazeX:.12,gazeY:-.02,lids:.73},
  hurt:{gazeX:-.22,gazeY:-.25,lids:.70},
  angry:{gazeX:0,gazeY:.02,lids:.77},
  withdrawn:{gazeX:-.35,gazeY:-.32,lids:.80},
});
export const clamp = (v,lo=0,hi=1)=>Math.max(lo,Math.min(hi,v));
// Cinematic staging assumptions, not dimensions measured from the KIRI scan.
export const ENCOUNTER_STAGE=Object.freeze({creatureFeet:8,visitorFeet:71/12,eyeInsetFeet:4/12,distanceFeet:5,headCenterFeet:7,waistFeet:4.2,unitsPerFoot:3.7/2});
export function entrancePose(seconds,reduced=false){
  const t=reduced?1:clamp((seconds-.45)/4.6),progress=t*t*t*(t*(6*t-15)+10);
  // Keep only a faint silhouette through the sit-up (ends at 5.05s),
  // hold upright for 0.65s, then ease into the full portrait illumination.
  const silhouette=reduced?1:clamp((seconds-1.2)/2.8);
  const r=reduced?1:clamp((seconds-5.7)/2.8);
  const reveal=.16*silhouette*silhouette*(3-2*silhouette)+.84*r*r*(3-2*r);
  // Keep the lids shut through the sit-up. Once upright, snap them open for
  // a brief startle, then ease back to the normal resting opening.
  const upright=progress>=1;
  const jump=reduced?1:clamp((seconds-5.05)/.28);
  const settleEyes=reduced?1:clamp((seconds-5.33)/1.15);
  const eyeOpen=reduced?1:upright?(jump<1?1.85*jump:1.85-(.85*settleEyes*settleEyes*(3-2*settleEyes))):0;
  const settle=clamp((progress-.65)/.35);
  // The visitor is on +Z. Reclining toward -Z places the head behind the
  // hips, face upward; rising then travels upward AND toward the visitor.
  // Keep the camera fixed and acquire the downward gaze only near upright.
  return {progress,reveal,lean:-(1-progress)*Math.PI/2,headPitch:.28*settle*settle*(3-2*settle),framing:1,eyeOpen,complete:t===1&&r===1&&upright&&settleEyes===1};
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
  reset(){this.jaw=0;this.x=0;this.y=0;this.lids=DIRECTIONS.curious.lids;this.neckSide=0;this.neckForward=0;this.silence=10;this.speechAge=10;}
  step(input,emotion,dt,blink=0){
    dt=clamp(dt,0,.05);
    const d=DIRECTIONS[emotion]||DIRECTIONS.curious;
    // Provisional visual slew limits, deliberately unrelated to unmeasured hardware speed.
    this.jaw=approach(this.jaw,clamp(input.open||0),input.open>this.jaw?5:7,dt);
    this.x=approach(this.x,d.gazeX,.65,dt);
    this.y=approach(this.y,d.gazeY,.5,dt);
    this.lids=approach(this.lids,Math.max(d.lids,blink),blink?8:2.8,dt);
    const forward={dormant:.22,curious:0,hopeful:-.12,engaged:-.04,wary:.10,hurt:.23,angry:-.1,withdrawn:.32}[emotion]||0;
    if(input.speaking){if(this.silence>.6)this.speechAge=0;this.silence=0;}else this.silence+=dt;
    this.speechAge+=dt;
    const nod=this.speechAge<1.4?Math.sin(this.speechAge/1.4*Math.PI)*.10:0;
    // Gaze acquires first; the neck follows with slower, restrained movement.
    this.neckSide=approach(this.neckSide,this.x,.22,dt);
    this.neckForward=approach(this.neckForward,forward+nod,.20,dt);
    return {CH4:this.y,CH5:this.y,CH6:this.x,CH7:this.x,CH8:this.lids,M1:this.jaw,NECK_SIDE:this.neckSide,NECK_FB:this.neckForward};
  }
}
