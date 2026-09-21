import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {AudioMotion,MechanicalPose,RIG,DIRECTIONS,ENCOUNTER_STAGE,entrancePose,clamp} from './motion-core.mjs';
import {buildBlenderHead} from './blender-head.mjs';

const host=document.querySelector('#creature-stage'),label=document.querySelector('#scene-state'),awakeningCue=document.querySelector('#awakening-cue');
const timeline=new AudioMotion(),pose=new MechanicalPose();
let context=null,direction='curious',phase='ready',last=performance.now(),nextBlink=7,blinkStart=-10;
let referenceAudio=null,referenceSamples=null,referenceEnvelope=null;
let cancelStudy=()=>{};
let finishEntrance=()=>{};
const diagnostics={ready:false,frames:0,pose:{},speaking:false,renderer:'Three.js r180 / KIRI scan GLB'};
window.creatureDiagnostics=diagnostics;
window.creatureSimulation={
  attachAudio(c){cancelStudy();context=c;},
  schedule(samples,rate,start,emotion){timeline.enqueue(samples,rate,start,emotion||direction);},
  setDirection(value){if(value)direction=value;},
  setPhase(value){phase=value;if(value==='connecting')finishEntrance();},
  stop(){cancelStudy();timeline.clear();pose.jaw=0;referenceAudio=null;},
  bindReference(audio,samples,rate){cancelStudy();referenceAudio=audio;referenceSamples=samples;referenceEnvelope=new AudioMotion();referenceEnvelope.enqueue(samples,rate,0,'curious');},
};
function dismissAwakeningCue(failed=false){
  if(!awakeningCue||awakeningCue.classList.contains('is-rendered'))return;
  if(failed){awakeningCue.classList.add('is-failed');awakeningCue.querySelector('.awakening-copy').textContent='The apparatus remains hidden. The voice may still answer.';}
  awakeningCue.classList.add('is-rendered');
  setTimeout(()=>{awakeningCue.hidden=true;},700);
}
init().catch(error=>{dismissAwakeningCue(true);window.encounterUI?.setEntranceComplete(true);label.textContent='3D preview unavailable — voice audition still works.';diagnostics.error=error.message;console.error(error);});

async function init(){
  const scene=new THREE.Scene();scene.background=new THREE.Color('#000000');
  const stage=ENCOUNTER_STAGE,unit=stage.unitsPerFoot;
  const visitorPosition=new THREE.Vector3(0,(stage.visitorFeet-stage.eyeInsetFeet-stage.headCenterFeet)*unit,stage.distanceFeet*unit);
  const lookTarget=new THREE.Vector3(0,-.03,0);
  const camera=new THREE.PerspectiveCamera(25,1,.1,80);camera.position.copy(visitorPosition);camera.lookAt(lookTarget);let restingFov=25;
  diagnostics.view={...stage,eyeHeightFeet:stage.visitorFeet-stage.eyeInsetFeet,lookUpDegrees:Math.atan2(lookTarget.y-visitorPosition.y,visitorPosition.z)*180/Math.PI};
  const touchDevice=matchMedia('(pointer:coarse)').matches;
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:!touchDevice});
  renderer.setPixelRatio(Math.min(devicePixelRatio,touchDevice?1.5:2));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
  renderer.domElement.setAttribute('aria-label','Blender Creature head with continuous mouth, eyes and neck motion');
  renderer.domElement.setAttribute('role','img');host.prepend(renderer.domElement);
  const ambient=new THREE.HemisphereLight(),key=new THREE.DirectionalLight(),rim=new THREE.DirectionalLight(),fill=new THREE.DirectionalLight();
  key.castShadow=true;key.shadow.mapSize.set(touchDevice?1024:2048,touchDevice?1024:2048);
  Object.assign(key.shadow.camera,{left:-3.8,right:3.8,top:3.8,bottom:-3.8,near:.1,far:18});
  key.shadow.bias=-.00015;key.shadow.normalBias=.015;key.shadow.camera.updateProjectionMatrix();
  scene.add(ambient,key,rim,fill);rim.position.set(3,2,-3);fill.position.set(2,0,5);
  const lightning=new THREE.DirectionalLight(0xdceaff,0);lightning.position.set(-2,4,5);scene.add(lightning);
  const neonGreen=new THREE.PointLight(0x43ffb2,0,7);neonGreen.position.set(-2,-1.8,2.5);
  const neonBlue=new THREE.PointLight(0x3b8dff,0,7);neonBlue.position.set(2,-.8,1.8);scene.add(neonGreen,neonBlue);
  const lightningControl=document.querySelector('#lighting-lightning'),testLightning=document.querySelector('#test-lightning');
  let lightningStarted=-Infinity,lightningDuration=100,lightningPower=10,lightningCount=0,lightningPeak=0,entranceCue=false,entranceCuePlayed=false,thunderContext=null,sparkStarted=-Infinity,sparkDuration=160,sparkNext=2.5,sparkCount=0;
  const backgroundBase=new THREE.Color(0x000000),backgroundFlash=new THREE.Color(0x294b45);
  let nextLightning=performance.now()+18000+Math.random()*22000;
  function strike(now){
    lightningStarted=now;lightningDuration=80+Math.random()*40;lightningPower=9+Math.random()*3;
    lightning.position.set(Math.random()<.5?-3:3,4,5);lightningCount++;lightningPeak=0;
    nextLightning=now+18000+Math.random()*22000;
  }
  function playEntranceThunder(){
    // This is deliberately synthesized locally: no audio asset or network
    // request is needed during the password-to-laboratory transition.
    try{
      thunderContext=thunderContext||new AudioContext();
      const ctx=thunderContext;
      const play=()=>{
        const now=ctx.currentTime+.02;
        const crack=ctx.createBufferSource(),buffer=ctx.createBuffer(1,Math.floor(ctx.sampleRate*.065),ctx.sampleRate),data=buffer.getChannelData(0);
        for(let i=0;i<data.length;i++){const fall=1-i/data.length;data[i]=(Math.random()*2-1)*fall*fall;}
        crack.buffer=buffer;
        const crackGain=ctx.createGain();crackGain.gain.setValueAtTime(.22,now);crackGain.gain.exponentialRampToValueAtTime(.001,now+.065);crack.connect(crackGain).connect(ctx.destination);crack.start(now);crack.stop(now+.07);
        const rumble=ctx.createOscillator(),rumbleGain=ctx.createGain(),filter=ctx.createBiquadFilter();
        rumble.type='sawtooth';rumble.frequency.setValueAtTime(74,now+.06);rumble.frequency.exponentialRampToValueAtTime(31,now+1.55);
        filter.type='lowpass';filter.frequency.value=180;rumbleGain.gain.setValueAtTime(.0001,now+.06);rumbleGain.gain.exponentialRampToValueAtTime(.055,now+.18);rumbleGain.gain.exponentialRampToValueAtTime(.0001,now+1.6);
        rumble.connect(filter).connect(rumbleGain).connect(ctx.destination);rumble.start(now+.06);rumble.stop(now+1.65);
      };
      if(ctx.state==='suspended')ctx.resume().then(play).catch(()=>{});else play();
    }catch{}
  }
  const lightingPresets={
    // Low frontal green light catches the underside of the brow and nose;
    // restrained fill/rim leave the upper skull and far cheek in darkness.
    laboratory:{sky:0x627467,ground:0x050706,ambient:.018,key:0xa6c798,power:1.16,position:[-1.2,-5.5,2.0],rim:0x71879c,rimPower:.10,fill:.26,fillColor:0x9baf9e,fillPosition:[0,.2,4]},
    moody:{sky:0xb2bfcd,ground:0x171b20,ambient:.38,key:0xffdfb7,power:1.65,position:[-4,5,2.5],rim:0x88b8d0,rimPower:1.25,fill:.10,background:0x070b0e},
    moonlight:{sky:0x8eacc8,ground:0x10151c,ambient:.28,key:0xb5cee8,power:1.45,position:[-3,4,3],rim:0x779fca,rimPower:1.5,fill:.12,background:0x060a12},
    studio:{sky:0xffffff,ground:0x34382a,ambient:2,key:0xffffff,power:2,position:[-3,4,4],rim:0xffffff,rimPower:0,fill:0,background:0x0c1110},
  };
  const lightingSelect=document.querySelector('#lighting-preset'),lightingLevel=document.querySelector('#lighting-level'),lightingValue=document.querySelector('#lighting-value'),flickerControl=document.querySelector('#lighting-flicker');
  // A new lighting revision makes the requested laboratory look the initial
  // choice, then remembers subsequent adjustments without overwriting old ones.
  const lightingStorage='creature-lighting-laboratory-v1';
  try{const saved=JSON.parse(localStorage.getItem(lightingStorage)||'null');if(saved&&lightingPresets[saved.preset]){lightingSelect.value=saved.preset;if(Number.isFinite(saved.level))lightingLevel.value=clamp(saved.level,50,150);flickerControl.checked=saved.flicker!==false;lightningControl.checked=saved.lightning!==false;}}catch{}
  function applyLighting(){
    const p=lightingPresets[lightingSelect.value]||lightingPresets.laboratory,level=Number(lightingLevel.value),gain=level/100;
    ambient.color.setHex(p.sky);ambient.groundColor.setHex(p.ground);ambient.intensity=p.ambient*gain;
    key.color.setHex(p.key);key.intensity=p.power*gain;key.position.set(...p.position);
    rim.color.setHex(p.rim);rim.intensity=p.rimPower*gain;fill.color.setHex(p.fillColor||p.sky);fill.position.set(...(p.fillPosition||[2,0,5]));fill.intensity=p.fill*gain;
    scene.background.setHex(0x000000);lightingValue.value=level+'%';
    flickerControl.disabled=lightingSelect.value!=='laboratory';
    lightningControl.disabled=lightingSelect.value!=='laboratory';testLightning.disabled=lightningControl.disabled||!lightningControl.checked;
    diagnostics.lighting={preset:lightingSelect.value,level,flicker:flickerControl.checked,lightning:lightningControl.checked};host.dataset.lighting=JSON.stringify(diagnostics.lighting);
    try{localStorage.setItem(lightingStorage,JSON.stringify(diagnostics.lighting));}catch{}
  }
  lightingSelect.addEventListener('change',applyLighting);lightingLevel.addEventListener('input',applyLighting);flickerControl.addEventListener('change',applyLighting);lightningControl.addEventListener('change',applyLighting);applyLighting();
  testLightning.addEventListener('click',()=>{
    if(lightingSelect.value==='laboratory'&&lightningControl.checked&&!reduced.matches)strike(performance.now());
  });
  function updateLightning(now){
    const cue=entranceCue&&now-lightningStarted<lightningDuration+50;
    const enabled=lightingSelect.value==='laboratory'&&lightningControl.checked&&!reduced.matches&&!document.hidden&&(entranceDone||cue);
    if(!enabled){lightningStarted=-Infinity;entranceCue=false;nextLightning=now+18000+Math.random()*22000;}
    else if(entranceDone&&now>=nextLightning)strike(now);
    const age=now-lightningStarted;
    // One short crack, not a repeating strobe. Use wall time so a slow frame
    // cannot stretch the flash; the stage and throat stay black throughout.
    const envelope=age>=0&&age<lightningDuration?1-THREE.MathUtils.smoothstep(age/lightningDuration,.20,1):0;
    lightning.intensity=enabled?lightningPower*envelope*Number(lightingLevel.value)/100:0;
    const bg=entranceCue?envelope*.30:0;scene.background.copy(backgroundBase).lerp(backgroundFlash,bg);
    lightningPeak=Math.max(lightningPeak,lightning.intensity);
    diagnostics.lightning={count:lightningCount,intensity:lightning.intensity,peak:lightningPeak,durationMs:lightningDuration};
  }
  // Smooth, irregular lamp fluctuations and occasional separate dropouts.
  // Another lamp always holds the face; reduced-motion uses steady illumination.
  function lampNoise(t){const i=Math.floor(t),f=THREE.MathUtils.smoothstep(t-i,0,1),hash=n=>{const v=Math.sin(n*127.1+31.7)*43758.5453;return v-Math.floor(v);};return THREE.MathUtils.lerp(hash(i),hash(i+1),f);}
  function updateLaboratoryLights(t){
    if(lightingSelect.value!=='laboratory')return;
    const gain=Number(lightingLevel.value)/100,p=lightingPresets.laboratory;
    const animate=flickerControl.checked&&!reduced.matches;
    const flickerMix=animate?THREE.MathUtils.smoothstep((performance.now()-entranceStarted)/1000,8.5,9.7):0;
    const drop=animate?1-THREE.MathUtils.smoothstep(lampNoise(t*.28),.68,.84):1;
    const warm=animate?THREE.MathUtils.smoothstep(lampNoise(t*.39+51),.20,.52)*(.78+.22*lampNoise(t*2.1+9)):1;
    key.intensity=p.power*gain*THREE.MathUtils.lerp(1,(.84+.16*lampNoise(t*2.6))*drop,flickerMix);
    fill.intensity=p.fill*gain*THREE.MathUtils.lerp(1,.60+.40*warm,flickerMix);
    rim.intensity=p.rimPower*gain*THREE.MathUtils.lerp(1,.84+.16*lampNoise(t*.65+19),flickerMix);
    const now=performance.now();
    if(!reduced.matches&&!document.hidden&&t>=sparkNext){sparkStarted=now;sparkDuration=90+Math.random()*150;sparkNext=t+2.8+Math.random()*5.4;sparkCount++;}
    const sparkAge=now-sparkStarted,sparkEnvelope=sparkAge>=0&&sparkAge<sparkDuration?Math.sin(Math.PI*sparkAge/sparkDuration):0;
    neonGreen.intensity=lightingSelect.value==='laboratory'?(0.025+0.22*sparkEnvelope)*gain:0;
    neonBlue.intensity=lightingSelect.value==='laboratory'?(0.018+0.16*Math.max(0,sparkEnvelope-.18))*gain:0;
    diagnostics.lampLevels=[key.intensity,fill.intensity,rim.intensity,neonGreen.intensity,neonBlue.intensity];diagnostics.sparks={count:sparkCount,intensity:sparkEnvelope};
  }
  const controls=new OrbitControls(camera,renderer.domElement);controls.enablePan=false;controls.enableDamping=true;
  controls.target.copy(lookTarget);controls.minDistance=6.5;controls.maxDistance=14;controls.update();
  // The scan includes the complete head and neck.
  controls.minAzimuthAngle=-Infinity;controls.maxAzimuthAngle=Infinity;
  controls.minPolarAngle=Math.PI/2-.7;controls.maxPolarAngle=Math.PI/2+.7;
  function resetView(){camera.position.copy(visitorPosition);camera.zoom=1;controls.target.copy(lookTarget);camera.updateProjectionMatrix();controls.update();}
  document.querySelector('#reset-view').onclick=()=>{finishEntrance();resetView();};
  const model=await buildBlenderHead();diagnostics.model=model.state;
  model.group.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  const waist=new THREE.Group(),headMount=new THREE.Group();waist.name='Presentation waist hinge';
  waist.position.y=(stage.waistFeet-stage.headCenterFeet)*unit;
  headMount.position.y=-waist.position.y;headMount.rotation.x=.28;
  headMount.add(model.group);waist.add(headMount);scene.add(waist);
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let entranceStarted=performance.now(),entranceDone=false;
  const replayEntrance=document.querySelector('#replay-entrance');
  finishEntrance=()=>{window.encounterUI?.setEntranceComplete(true);entranceDone=true;waist.rotation.x=0;headMount.rotation.x=.28;model.setReveal(1);camera.fov=restingFov;camera.updateProjectionMatrix();controls.enabled=true;};
  function updateEntrance(now){
    const value=entranceDone?entrancePose(10):entrancePose((now-entranceStarted)/1000,reduced.matches);
    waist.rotation.x=value.lean;headMount.rotation.x=value.headPitch;model.setReveal(value.reveal);controls.enabled=value.complete;
    // Supine-to-seated motion approaches from behind the hips. A fixed lens
    // preserves that physical arc instead of creating an artificial zoom.
    const fov=restingFov*value.framing;if(camera.fov!==fov){camera.fov=fov;camera.updateProjectionMatrix();}
    if(value.complete)entranceDone=true;
    if(!entranceCuePlayed&&!reduced.matches&&value.progress>=.78){
      entranceCuePlayed=true;entranceCue=true;strike(now);playEntranceThunder();
    }
    window.encounterUI?.setEntranceComplete(value.complete);
    diagnostics.entrance=value;host.dataset.entrance=JSON.stringify(value);return value;
  }
  if(document.querySelector('#start').disabled)finishEntrance();
  updateEntrance(entranceStarted);
  replayEntrance.onclick=()=>{if(document.querySelector('#start').disabled)return;cancelStudy();resetView();entranceStarted=performance.now();entranceDone=false;entranceCue=false;entranceCuePlayed=false;lightningStarted=-Infinity;sparkStarted=-Infinity;sparkNext=2.5;updateEntrance(entranceStarted);document.querySelector('#encounter-menu').close();};
  document.querySelector('#wireframe').onchange=e=>model.group.traverse(o=>{if(o.isMesh)for(const m of (Array.isArray(o.material)?o.material:[o.material]))m.wireframe=e.target.checked;});
  const meters=document.querySelector('#mechanism-meters');
  for(const [id,info] of Object.entries(RIG)){
    const row=document.createElement('div');row.className='mechanism-row';row.dataset.channel=id;row.title=info.evidence;
    const code=document.createElement('span');code.className='channel';code.textContent=id.startsWith('NECK')?'Neck':id;
    const text=document.createElement('span');text.textContent=info.label;
    const meter=document.createElement('meter');meter.min=0;meter.max=1;
    row.append(code,text,meter,document.createElement('output'));meters.append(row);
  }
  const neutral={CH4:0,CH5:0,CH6:0,CH7:0,CH8:DIRECTIONS.curious.lids,M1:0,NECK_SIDE:0,NECK_FB:0};
  let forced=null,studyStarted=null;
  // Deterministic poses for repeatable visual QA; no network or physical transport.
  window.creatureReview={
    setPose(p){forced=p?{...neutral,...p}:null;},
    reset(){forced=null;studyStarted=null;resetView();},
    camera(yaw=0,pitch=0){camera.position.set(8*Math.sin(yaw),8*Math.sin(pitch),8*Math.cos(yaw)*Math.cos(pitch));camera.lookAt(0,0,0);controls.update();},

  };
  const study=document.querySelector('#motion-study');
  cancelStudy=()=>{studyStarted=null;forced=null;study.textContent='Run movement study';};
  study.onclick=async()=>{
    if(studyStarted!==null){cancelStudy();return;}
    if(referenceAudio&&!referenceAudio.paused){
      const audio=referenceAudio;
      // Let the audio pause handler clear its motion before starting the study.
      await new Promise(resolve=>{audio.addEventListener('pause',resolve,{once:true});audio.pause();});
    }
    finishEntrance();forced=null;resetView();studyStarted=performance.now();study.textContent='Stop movement study';document.querySelector('#encounter-menu').close();
  };
  function studyPose(t){
    const p={...neutral};
    if(t<3)p.M1=(1-Math.cos(t/3*Math.PI*2))/2;
    else if(t<7)p.NECK_SIDE=Math.sin((t-3)/4*Math.PI*2)*.85;
    else if(t<11)p.NECK_FB=Math.sin((t-7)/4*Math.PI*2)*.85;
    else if(t<14){p.CH6=p.CH7=Math.sin((t-11)/3*Math.PI*2)*.7;}
    else if(t<17){p.CH4=p.CH5=Math.sin((t-14)/3*Math.PI*2)*.7;}
    else if(t<20){p.CH8=t<18?THREE.MathUtils.lerp(neutral.CH8,1,t-17):t<19?1:THREE.MathUtils.lerp(1,neutral.CH8,t-19);}
    return p;
  }
  function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;const half=Math.max(1.66,1.10*h/w);restingFov=2*Math.atan(half/visitorPosition.distanceTo(lookTarget))*180/Math.PI;camera.fov=restingFov;camera.updateProjectionMatrix();}
  new ResizeObserver(resize).observe(host);resize();
  let elapsed=0,lastUi=0,firstCreatureFrame=true;
  renderer.setAnimationLoop(()=>{
    const now=performance.now(),dt=Math.min((now-last)/1000,.05);last=now;elapsed+=dt;
    let current={open:0,rms:0,speaking:false};
    if(referenceAudio&&!referenceAudio.paused&&!referenceAudio.ended&&referenceEnvelope){
      if(referenceAudio.currentTime<(referenceEnvelope.lastTime||0)){referenceEnvelope.clear();referenceEnvelope.enqueue(referenceSamples,referenceAudio.__sampleRate,0,'curious');}
      current=referenceEnvelope.at(referenceAudio.currentTime);referenceEnvelope.lastTime=referenceAudio.currentTime;
    }else if(context&&context.state==='running'){
      const stamp=context.getOutputTimestamp?.();let t=context.currentTime-(context.outputLatency||0);
      if(stamp?.performanceTime>0)t=stamp.contextTime+(now-stamp.performanceTime)/1000;
      current=timeline.at(t);
    }
    if(current.emotion)direction=current.emotion;
    if(!entranceDone)nextBlink=elapsed+4;
    if(entranceDone&&!reduced.matches&&elapsed>nextBlink){blinkStart=elapsed;nextBlink=elapsed+5.5+(Math.sin(elapsed*2)+1)*1.9;}
    // Brief closed hold lets the linked lids meet before reopening.
    const age=elapsed-blinkStart,blink=age<0||age>=.32?0:age<.10?age/.10:age<.15?1:1-(age-.15)/.17;
    let p=pose.step(current,direction,dt,blink);
    if(studyStarted!==null){const t=(now-studyStarted)/1000;if(t>20){studyStarted=null;study.textContent='Run movement study';}else p=studyPose(t);}
    if(forced)p=forced;
    const entry=updateEntrance(now);
    p.CH8=THREE.MathUtils.lerp(1,p.CH8,entry.eyeOpen);
    controls.update();model.update(p,camera.position,entry.complete);diagnostics.gaze=model.state.gaze;
    // The Blender pivot carries the whole head, wig and terminals together.
    updateLaboratoryLights(elapsed);updateLightning(now);renderer.render(scene,camera);
    if(firstCreatureFrame){firstCreatureFrame=false;dismissAwakeningCue();}
    diagnostics.frames++;diagnostics.pose=p;diagnostics.speaking=current.speaking;diagnostics.direction=direction;diagnostics.phase=phase;diagnostics.queuedSegments=timeline.segments.length;
    diagnostics.triangles=renderer.info.render.triangles;
    if(now-lastUi>100){lastUi=now;
      renderer.domElement.dataset.rigState=JSON.stringify({...model.state,frames:diagnostics.frames});
      host.dataset.lampLevels=JSON.stringify(diagnostics.lampLevels||[]);
      host.dataset.lightning=JSON.stringify(diagnostics.lightning);
      host.dataset.view=JSON.stringify(diagnostics.view);
      label.textContent=studyStarted!==null?'Movement study':current.speaking?'Speaking · '+direction:phase==='connected'?'Listening':'At rest';
      study.disabled=document.querySelector('#start').disabled;
      replayEntrance.disabled=study.disabled;
      document.querySelector('#emotion-name').textContent=direction;
      document.querySelector('#jaw-level').style.width=(p.M1*100)+'%';
      for(const row of meters.children){const id=row.dataset.channel,value=p[id];row.querySelector('meter').value=id==='M1'||id==='CH8'?value:(value+1)/2;row.querySelector('output').textContent=Math.round(value*100)+'%';}
    }
  });
  diagnostics.ready=true;label.textContent='At rest';
}
