import test from 'node:test';
import assert from 'node:assert/strict';
import {AudioMotion,MechanicalPose,audioEnvelope,RIG,HEAD_CHANNELS,AUX_SIGNALS,DIRECTIONS,EMOTION_PROFILES,CUES,ENCOUNTER_STAGE,entrancePose} from './motion-core.mjs';

test('head-channel table maps confirmed PCA outputs and shared bolt signal',()=>{
  assert.deepEqual(Object.fromEntries(Object.entries(HEAD_CHANNELS).map(([id,value])=>[id,value.pca])),{
    CH1:'PWM5',CH2:'PWM6',CH3:'PWM7',CH4:'PWM0',CH5:'PWM1',CH6:'PWM2',CH7:'PWM3',CH8:'PWM4',
  });
  for(const id of Object.keys(HEAD_CHANNELS))assert.equal(HEAD_CHANNELS[id].confirmed,true);
  assert.equal(AUX_SIGNALS.LED_BOLTS.confirmed,true);
});

test('jaw follows PCM energy, with silence closed and loud input bounded',()=>{
  assert.equal(audioEnvelope(new Float32Array(441))[0].open,0);
  const soft=audioEnvelope(new Float32Array(441).fill(.05))[0];
  const loud=audioEnvelope(new Float32Array(441).fill(.9))[0];
  assert.ok(soft.open>0&&soft.open<loud.open);
  assert.equal(loud.open,1);
});

test('motion and direction start at audio playback time, not enqueue time',()=>{
  const timeline=new AudioMotion();
  timeline.enqueue(new Float32Array(4410).fill(.1),44100,10,'hurt');
  assert.deepEqual(timeline.at(9.999),{open:0,rms:0,speaking:false});
  assert.equal(timeline.at(10.02).emotion,'hurt');
  assert.ok(timeline.at(10.02).open>0);
  assert.equal(timeline.at(10.11).speaking,false);
  assert.equal(timeline.at(10.11).open,0);
});

test('gaps remain silent, and cancellation removes all scheduled motion',()=>{
  const timeline=new AudioMotion(),samples=new Float32Array(4410).fill(.1);
  timeline.enqueue(samples,44100,0,'hopeful');
  timeline.enqueue(samples,44100,.3,'wary');
  assert.equal(timeline.at(.05).emotion,'hopeful');
  assert.equal(timeline.at(.2).open,0);
  assert.equal(timeline.at(.32).emotion,'wary');
  timeline.clear();
  assert.equal(timeline.at(.35).open,0);
  assert.equal(timeline.segments.length,0);
});

test('the rig exposes only supported axes, respects slew, and closes on silence',()=>{
  const pose=new MechanicalPose();
  const first=pose.step({open:20},'wary',1);
  assert.deepEqual(Object.keys(first).sort(),Object.keys(RIG).sort());
  assert.equal(first.M1,.25); // capped dt and visual opening speed
  assert.equal(first.CH4,first.CH5);
  assert.equal(first.CH6,first.CH7);
  for(const direction of Object.keys(DIRECTIONS)){
    for(let i=0;i<100;i++){
      const p=pose.step({open:i%2},direction,1/60,i%10===0?1:0);
      assert.ok(p.M1>=0&&p.M1<=1);
      assert.ok(p.CH8>=0&&p.CH8<=1);
      for(const id of ['CH4','CH5','CH6','CH7'])assert.ok(Math.abs(p[id])<=1);
    }
  }
  for(let i=0;i<20;i++)pose.step({open:0},'curious',1/60);
  assert.equal(pose.jaw,0);
});

test('emotion controls supported gaze and lid axes',()=>{
  const pose=new MechanicalPose();
  let p;
  for(let i=0;i<100;i++)p=pose.step({open:0},'withdrawn',1/60);
  assert.equal(p.M1,0);
  assert.equal(p.CH4,DIRECTIONS.withdrawn.gazeY);
  assert.equal(p.CH6,DIRECTIONS.withdrawn.gazeX);
  assert.equal(p.CH8,DIRECTIONS.withdrawn.lids);
});

test('emotion profiles produce distinct, bounded body language',()=>{
  const settled={};
  for(const emotion of Object.keys(EMOTION_PROFILES)){
    const pose=new MechanicalPose();let p;
    for(let i=0;i<360;i++)p=pose.step({open:0,speaking:false},emotion,1/60);
    settled[emotion]=[p.CH1,p.CH2,p.CH3,p.CH4,p.CH6,p.CH8,p.LED_BOLTS];
    for(const id of Object.keys(RIG))assert.ok(p[id]>=-1&&p[id]<=1,`${emotion} ${id} out of range`);
  }
  assert.notDeepEqual(settled.curious,settled.hopeful);
  assert.notDeepEqual(settled.hopeful,settled.wary);
  assert.notDeepEqual(settled.hurt,settled.withdrawn);
  assert.ok(settled.hopeful.at(-1)>settled.curious.at(-1));
  assert.ok(settled.angry.at(-1)>settled.wary.at(-1));
});

test('readable states add sustained semantics without breaking paired attention',()=>{
  const attentive=new MechanicalPose(),suspicious=new MechanicalPose();
  let a,s;
  for(let i=0;i<180;i++){
    a=attentive.step({open:0,speaking:false},'attentive',1/60);
    s=suspicious.step({open:0,speaking:false},'suspicious',1/60);
  }
  assert.equal(a.CH4,a.CH5);
  assert.equal(a.CH6,a.CH7);
  assert.ok(Math.abs(s.CH6-s.CH7)>.04,'suspicion should read as a side-eye');
  assert.ok(s.CH8>a.CH8,'suspicion should narrow the lids');
  assert.ok(Math.abs(s.CH2)>Math.abs(a.CH2),'suspicion should turn the head');
});

test('expressive mode amplifies emotion and cues without leaving normalized bounds',()=>{
  const restrained=new MechanicalPose(),expressive=new MechanicalPose();
  expressive.setExpressive(true);restrained.setCue('disagree');expressive.setCue('disagree');
  let quiet,emphatic;
  for(let i=0;i<120;i++){
    quiet=restrained.step({open:0,speaking:false},'wary',1/60);
    emphatic=expressive.step({open:0,speaking:false},'wary',1/60);
    for(const id of Object.keys(RIG))assert.ok(emphatic[id]>=-1&&emphatic[id]<=1,`${id} out of range`);
  }
  assert.ok(Math.abs(emphatic.CH6)>Math.abs(quiet.CH6));
  assert.ok(Math.abs(emphatic.CH1)>Math.abs(quiet.CH1));
  assert.ok(emphatic.CH8>quiet.CH8);
  const engaged=new MechanicalPose();engaged.setExpressive(true);let minScan=Infinity,maxScan=-Infinity;
  for(let i=0;i<240;i++){const frame=engaged.step({open:0,speaking:true},'engaged',1/60);minScan=Math.min(minScan,frame.CH6);maxScan=Math.max(maxScan,frame.CH6);}
  assert.ok(maxScan-minScan>.06,'engaged gaze should visibly scan side to side');
  assert.ok(engaged.lids>DIRECTIONS.curious.lids,'engaged eyelids should narrow');
  expressive.setExpressive(false);
  const restored=new MechanicalPose();
  for(let i=0;i<120;i++){expressive.step({open:0,speaking:false},'wary',1/60);restored.step({open:0,speaking:false},'wary',1/60);}
  assert.deepEqual(expressive.step({open:0,speaking:false},'wary',1/60),restored.step({open:0,speaking:false},'wary',1/60));
});

test('speech emphasis is phrase-level rather than syllable-level',()=>{
  const pose=new MechanicalPose();
  pose.step({open:0,speaking:false},'angry',1/60);
  let first=pose.step({open:.8,rms:.2,speaking:true},'angry',1/60);
  assert.ok(pose.accent>.9);
  const accentAtStart=pose.accent;
  for(let i=0;i<8;i++)pose.step({open:.8,rms:.2,speaking:true},'angry',1/60);
  assert.ok(pose.accent<accentAtStart);
  const held=pose.accent;
  for(let i=0;i<8;i++)pose.step({open:.8,rms:.2,speaking:true},'angry',1/60);
  assert.ok(pose.accent<=held);
  assert.ok(first.M1>0&&first.LED_BOLTS>=0&&first.LED_BOLTS<=1);
});

test('semantic cues create bounded gestures and then expire',()=>{
  const pose=new MechanicalPose();
  const signatures={};
  for(const cue of Object.keys(CUES)){
    pose.reset();pose.setCue(cue);let minY=Infinity,maxY=-Infinity,minRot=Infinity,maxRot=-Infinity,minFlex=Infinity,maxFlex=-Infinity;
    for(let i=0;i<90;i++){
      const p=pose.step({open:0,rms:0,speaking:false},'curious',1/60);
      minY=Math.min(minY,p.CH4);maxY=Math.max(maxY,p.CH4);minRot=Math.min(minRot,p.CH2);maxRot=Math.max(maxRot,p.CH2);
      minFlex=Math.min(minFlex,p.CH1);maxFlex=Math.max(maxFlex,p.CH1);
      for(const id of Object.keys(RIG))assert.ok(p[id]>=-1&&p[id]<=1,`${cue} ${id} out of range`);
    }
    signatures[cue]=[minY,maxY,minRot,maxRot,minFlex,maxFlex];
  }
  assert.ok(signatures.think[1]>signatures.none[1]);
  assert.ok(signatures.disagree[2]<signatures.disagree[3]);
  assert.ok(signatures.agree[4]<signatures.agree[5]);
  assert.equal(pose.cueName,'none');
});

test('returning from withdrawal to curious settles at straight-ahead gaze and head pose',()=>{
  const pose=new MechanicalPose();let p;
  for(let i=0;i<180;i++)pose.step({open:0},'withdrawn',1/60);
  for(let i=0;i<180;i++)p=pose.step({open:0},'curious',1/60);
  for(const channel of ['CH1','CH2','CH3','CH4','CH5','CH6','CH7','LED_BOLTS'])assert.equal(p[channel],0);
});

test('linked eyelids can close fully and reopen without disturbing gaze or mouth',()=>{
  const pose=new MechanicalPose();let p;
  for(let i=0;i<30;i++)p=pose.step({open:0},'curious',1/60,1);
  assert.equal(p.CH8,1);
  for(const c of ['CH4','CH5','CH6','CH7','M1'])assert.equal(p[c],0);
  for(let i=0;i<60;i++)p=pose.step({open:0},'curious',1/60,0);
  assert.equal(p.CH8,DIRECTIONS.curious.lids);
});


test('entrance rises continuously from darkness and settles without looping',()=>{
  let previous=entrancePose(0);
  assert.equal(previous.reveal,.22);assert.equal(previous.complete,false);
  assert.equal(previous.lean,-Math.PI/2);assert.equal(previous.headPitch,0);
  assert.ok(entrancePose(.1).progress>0);
  const radius=(ENCOUNTER_STAGE.headCenterFeet-ENCOUNTER_STAGE.waistFeet)*ENCOUNTER_STAGE.unitsPerFoot;
  let priorHeight=0,priorDepth=-radius;
  for(let frame=1;frame<=540;frame++){
    const current=entrancePose(frame/60);
    assert.ok(current.progress>=previous.progress);assert.ok(current.reveal>=previous.reveal);
    assert.ok(current.lean>=previous.lean);assert.equal(current.framing,1);
    // Actual hinge path: starts behind the waist, then moves up and forward.
    const height=radius*Math.cos(current.lean),depth=radius*Math.sin(current.lean);
    assert.ok(height>=priorHeight-1e-12);assert.ok(depth>=priorDepth-1e-12);assert.ok(depth<=0);
    assert.ok(current.headPitch>=previous.headPitch&&current.headPitch<=.28);
    priorHeight=height;priorDepth=depth;
    previous=current;
  }
  assert.equal(Math.abs(previous.lean),0);assert.equal(previous.headPitch,.28);assert.equal(previous.reveal,1);assert.equal(previous.complete,true);
  assert.deepEqual(entrancePose(60),entrancePose(10));
});

test('reduced-motion skips the rise and staging preserves requested relative scale',()=>{
  assert.deepEqual(entrancePose(0,true),entrancePose(10));
  const s=ENCOUNTER_STAGE;
  assert.equal(s.creatureFeet,8);assert.equal(s.visitorFeet*12,71);assert.equal(s.distanceFeet,5);
  assert.ok(s.waistFeet<s.visitorFeet-s.eyeInsetFeet);
  const elevation=Math.atan2(s.headCenterFeet-(s.visitorFeet-s.eyeInsetFeet),s.distanceFeet)*180/Math.PI;
  assert.ok(elevation>15&&elevation<18);
});

test('entrance is immediately legible, then holds low-key light until after the rise',()=>{
  assert.ok(entrancePose(1.2).reveal>.22);
  assert.ok(Math.abs(entrancePose(4).reveal-.34)<1e-12);
  const upright=entrancePose(5.1);
  assert.equal(upright.progress,1);assert.ok(Math.abs(upright.reveal-.34)<1e-12);assert.equal(upright.complete,false);
  assert.ok(Math.abs(entrancePose(5.7).reveal-.34)<1e-12);
  assert.ok(Math.abs(entrancePose(7.1).reveal-.67)<1e-12);
  assert.equal(entrancePose(8.5).reveal,1);assert.equal(entrancePose(8.5).complete,true);
  assert.equal('lightningCue' in upright,false);
});

test('eyes stay closed until full light, startle open, then return to rest',()=>{
  for(let frame=0;frame<=509;frame++)assert.equal(entrancePose(frame/60).eyeOpen,0);
  assert.ok(entrancePose(8.6).eyeOpen>0&&entrancePose(8.6).eyeOpen<1);
  assert.ok(entrancePose(8.74).eyeOpen>1);
  assert.equal(entrancePose(9.84).eyeOpen,1);
  assert.equal(entrancePose(8.5).complete,true);
  assert.equal(entrancePose(0,true).eyeOpen,1);
});
