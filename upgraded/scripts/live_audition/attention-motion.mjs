// One target composition for the twin and the opt-in physical bridge.
// Times are milliseconds; dt is seconds. This does not write servo outputs.
const HEAD=['CH1','CH2','CH3'],GAZE=[...HEAD,'CH4','CH5','CH6','CH7'];
export class AttentionMotion {
 constructor(){this.reset();}
 reset(){this.weight=0;this.track=null;this.acquiredAt=0;this.headHold={};this.permitted=false;}
 compose({pose,gaze,easedPose,now,dt,permitted=false,exclusive=false}){
  if(!Number.isFinite(now)||!Number.isFinite(dt)||dt<0)throw new TypeError('Finite motion clock required');
  const acquiring=gaze.trackId!==this.track||(permitted&&!this.permitted&&gaze.tracking);
  if(acquiring){this.track=gaze.trackId??null;this.acquiredAt=now;this.headHold={...easedPose};}
  this.permitted=permitted;
  const target={...pose,...gaze.pose};
  if(gaze.tracking&&now-this.acquiredAt<200)for(const id of HEAD)target[id]=this.headHold[id]??0;
  this.weight+=(Number(permitted)-this.weight)*(1-Math.exp(-Math.min(dt,.1)/.18));
  if(exclusive)this.weight=0;
  const output={...pose};
  for(const id of GAZE)output[id]=pose[id]*(1-this.weight)+target[id]*this.weight;
  return output;
 }
}
