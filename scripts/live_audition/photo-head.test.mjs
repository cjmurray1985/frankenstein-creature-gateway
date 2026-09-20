import test from 'node:test';
import assert from 'node:assert/strict';
import {mouthOffset,depth,bounds,LANDMARKS} from './photo-head.mjs';
import {MechanicalPose} from './motion-core.mjs';

test('mouth opens inside continuous skin; chin, neck, cheeks and nose stay anchored',()=>{
  for(const open of [0,.25,.5,.75,1]){
    for(const [x,y] of [LANDMARKS.chin,LANDMARKS.neck,LANDMARKS.nose,[800,674],[1040,674],[921,580]])assert.equal(mouthOffset(x,y,open),0);
    const upper=663+mouthOffset(921,663,open),lower=684+mouthOffset(921,684,open);
    assert.ok(Math.abs((lower-upper)-(2+38*open))<1e-8);
  }
});

test('skin deformation never folds vertically through its opening/closing range',()=>{
  for(let open=0;open<=1;open+=.1)for(let x=822;x<1021;x+=3){
    let previous=-Infinity;
    for(let y=580;y<815;y+=.5){const next=y+mouthOffset(x,y,open);assert.ok(next>previous,`fold at ${x},${y},${open}`);previous=next;}
  }
});

test('head volume remains finite at silhouette and measured landmark locations',()=>{
  for(let y=18;y<=974;y+=2){
    const [l,r]=bounds(y);assert.ok(r>l);
    for(let x=l;x<=r;x+=3)assert.ok(Number.isFinite(depth(x,y)));
  }
});

test('neck has both supported motions, bounded velocity, and no per-syllable bobbing',()=>{
  const p=new MechanicalPose();let previous=p.step({open:0,speaking:false},'curious',.05);
  const samples=[];
  for(let i=0;i<400;i++){
    const pose=p.step({open:i%2,speaking:true},'withdrawn',.05);
    assert.ok(Math.abs(pose.NECK_SIDE-previous.NECK_SIDE)<=.011001);
    assert.ok(Math.abs(pose.NECK_FB-previous.NECK_FB)<=.010001);
    assert.ok(Math.abs(pose.NECK_SIDE)<=1&&Math.abs(pose.NECK_FB)<=1);
    previous=pose;samples.push(pose);
  }
  assert.equal(samples.at(-1).NECK_SIDE,-.35);assert.equal(samples.at(-1).NECK_FB,.32);
  assert.ok(samples.slice(100).every(v=>v.NECK_FB===.32));
});
