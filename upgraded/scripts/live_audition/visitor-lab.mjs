import {RehearsalRecords} from './rehearsal-records.mjs';
import {DIRECTIONS} from './motion-core.mjs';
import {EMOTIONAL_GAUNTLET,REPAIR_STUDY,performanceProgress} from './emotion-rehearsal.mjs';
import {sampleScenario} from './visitor-scenarios.mjs';
const catalog=await (await fetch('/visitor-scenarios.json')).json();
const memoryCatalog=await (await fetch('/memory-scenarios.json')).json();
// Synthetic visitor rehearsal, isolated from physical actuation.
const labSession=crypto.randomUUID();
const scenarioRecords=new RehearsalRecords();
const token=document.querySelector('meta[name="hardware-token"]').content;
const panel=document.createElement('details');panel.className='menu-section';
panel.innerHTML=`<summary>Visitor tracking & memory rehearsal</summary>
<p class="fine">Synthetic visitors only. No Pi, camera, voice provider, Archive or real visitor profiles are used. Rehearsal profiles stay in server memory and clear on restart. Track IDs do not identify people.</p>
<label><input id="lab-enable" type="checkbox"> Rehearse with the virtual twin</label>
<div id="lab-controls" hidden>
<label>Scenario <select id="lab-scenario"><option value="manual">Manual visitors</option><option value="approach">Approach and departure</option><option value="group">Group / target switching</option><option value="stale">Camera interruption</option><option value="crossing">Crossing / brief occlusion</option></select></label>
<button id="lab-run">Run scenario</button><button id="lab-pause">Stop scenario</button>
<div id="lab-visitors"></div><label><input id="lab-stale" type="checkbox"> Simulate stale camera data</label>
<p id="lab-tracking" role="status"></p><p class="fine">Synthetic gaze starts centered at a 6 ft visitor. Camera calibration is restored when rehearsal ends. Scenarios use a shared, deterministic input catalog.</p>
<h3>Silent emotional performance</h3>
<label>Emotion <select id="lab-emotion">${Object.keys(DIRECTIONS).map(e=>`<option value="${e}" ${e==='curious'?'selected':''}>${e}</option>`).join('')}</select></label>
<button id="lab-emotion-apply">Hold selected emotion</button>
<button id="lab-gauntlet">Run emotional gauntlet</button><button id="lab-repair">Run trust / repair arc</button><button id="lab-emotion-stop">Stop performance</button>
<label><input id="lab-repeat" type="checkbox"> Repeat silent performance</label>
<label><input id="lab-expression-only" type="checkbox" checked> Study emotion without visitor gaze</label>
<p id="lab-performance" role="status">No scripted performance running.</p>
<p class="fine">These authored reactions are synthetic. No audio is generated. The study holds the camera and rig calibration unchanged.</p>
<h3>Returning-visitor memory</h3>
<label>Memory story <select id="lab-memory-story">${Object.entries(memoryCatalog.scenarios).map(([id,s])=>`<option value="${id}">${s.label}</option>`).join('')}</select></label>
<button id="lab-memory-run">Run memory story</button><button id="lab-memory-stop">Stop memory story</button>
<p class="fine">Stories reset this page's synthetic profiles first. They apply explicit scripted visitor words; no generated reply or voice.</p>
<p id="lab-memory-beat" role="status">No memory story running.</p>
<label>Synthetic profile <select id="lab-profile"><option value="lab-a">Visitor A</option><option value="lab-b">Visitor B</option><option value="lab-anonymous">Anonymous / no memory</option></select></label>
<button data-action="begin">Begin / return</button><button data-action="complete">Complete encounter</button><button data-action="discard">Discard encounter</button>
<label>Synthetic visitor words <textarea id="lab-text" maxlength="500" rows="2">My name is Clara. I promise I will come back.</textarea></label>
<button id="lab-turn">Apply words</button>
<div><button data-words="You deserve kindness. I will stay with you.">Kindness</button><button data-words="I do not trust you.">Suspicion</button><button data-words="Go away, you ugly monster.">Hostility</button><button data-words="What was that? You startled me.">Startle</button></div>
<button data-action="advance">Advance 14 days</button><button data-action="forget">Forget selected profile</button><button data-action="reset">Reset rehearsal memory</button><button id="lab-export">Download rehearsal report</button>
<pre id="lab-memory" class="fine" style="white-space:pre-wrap"></pre>
</div><p id="lab-status" role="status">Rehearsal off.</p>`;
document.querySelector('.menu-heading').after(panel);
const hud=document.createElement('output');hud.id='lab-hud';hud.className='rehearsal-hud';hud.hidden=true;hud.setAttribute('aria-label','Synthetic rehearsal status');document.querySelector('.stage-shell').append(hud);
const q=id=>panel.querySelector('#'+id),enabled=q('lab-enable');
const people=[{track_id:'sim-a',x:.5,y:.5,distance_ft:6,visible:true},{track_id:'sim-b',x:.72,y:.5,distance_ft:10,visible:false},{track_id:'sim-c',x:.25,y:.5,distance_ft:13,visible:false}];
const managedControls=['hardware-connect','start','preview','vision-observe','vision-gaze','vision-gain','vision-invert-x','vision-invert-y','vision-distance','vision-fov','vision-center'];
const gazeFields=[['vision-gain','gain'],['vision-invert-x','invertX'],['vision-invert-y','invertY'],['vision-distance','distanceInches'],['vision-fov','horizontalFovDegrees']];
function syncGazeControls(){for(const [id,key] of gazeFields){const e=document.getElementById(id);if(e.type==='checkbox')e.checked=window.creatureVisionGaze[key];else e.value=window.creatureVisionGaze[key];}}
let epoch=0,generation=0,scenarioStart=null,report=null,baseline=null,scenario='manual',trackingTrace=[],performanceRun=null,performanceIndex=-1,performanceTrace=[],performanceFrame=null,memoryBusy=false,memoryStory=null,memoryTimer=null;
for(const p of people){
 const row=document.createElement('fieldset');row.innerHTML=`<legend>${p.track_id}</legend><label><input type="checkbox" data-key="visible" ${p.visible?'checked':''}> Present</label><label>Horizontal <input type="range" data-key="x" min="0.05" max="0.95" step="0.01" value="${p.x}"></label><label>Face height in camera <input type="range" data-key="y" min="0.08" max="0.92" step="0.01" value="${p.y}"></label><label>Distance (ft) <input type="number" data-key="distance_ft" min="2" max="25" step="0.5" value="${p.distance_ft}"></label>`;
 row.oninput=e=>{const key=e.target.dataset.key;if(!key)return;p[key]=key==='visible'?e.target.checked:Number(e.target.value);scenarioRecords.finish('manual-change',performance.now());scenarioStart=null;scenario='manual';q('lab-status').textContent='Scenario interrupted by manual visitor control.';};q('lab-visitors').append(row);p.row=row;
}
function syncInputs(){for(const p of people)for(const e of p.row.querySelectorAll('[data-key]'))if(e.dataset.key==='visible')e.checked=p.visible;else e.value=p[e.dataset.key];}
async function request(action,extra={}){
 const response=await fetch('/visitor-lab',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,lab_session:labSession,action,...extra}),signal:AbortSignal.timeout(2000)});
 const value=await response.json();if(!response.ok)throw Error(value.error||'Rehearsal request failed');return value;
}
function memoryResult(value){
 report=value;
 const open=value.encounter_open;
 for(const b of panel.querySelectorAll('[data-action]')){const action=b.dataset.action;b.disabled=memoryBusy||(action==='begin'?open:['complete','discard'].includes(action)?!open:['advance','forget'].includes(action)?open:false);}
 for(const b of panel.querySelectorAll('[data-words],#lab-turn'))b.disabled=memoryBusy||!open;
 const state=value.state,context=value.context;
 q('lab-memory').textContent=JSON.stringify({simulated_time:value.now,profile:value.visitor,encounter_open:value.encounter_open,relationship:state?.relationship||value.committed_state?.relationship,emotion:state?.momentary,context,committed_memories:value.memories,retrieval_provenance:value.retrievals,pending_until_completion:value.pending_facts,events:value.events.slice(-8)},null,2);
 if(enabled.checked&&!performanceRun){
  window.creatureSimulation?.setDirection(state?.momentary.emotion||'curious');
  // Strong reactions hold priority briefly; ordinary gaze then resumes.
  window.creatureVisitorLab.emotion=state?.momentary.emotion||'curious';
 }
}
function scenarioPositions(t){
 const frame=sampleScenario(catalog.scenarios[scenario],t);
 for(const p of people){const source=frame.people.find(v=>v.track_id===p.track_id);p.visible=Boolean(source);if(source)Object.assign(p,source);}
 q('lab-stale').checked=frame.stale;
 syncInputs();if(t>=catalog.duration_seconds){scenarioStart=null;q('lab-status').textContent='Scenario finished. Manual controls remain active.';}
}
async function poll(g){
 if(!enabled.checked||g!==generation)return;
 if(scenarioStart!==null)scenarioPositions((performance.now()-scenarioStart)/1000);
 window.creatureVisitorLab.expressionStudy=Boolean(performanceRun&&q('lab-expression-only').checked);
 try{
  const o=await request('observe',{people:people.filter(p=>p.visible).map(({row,visible,...p})=>p),stale:q('lab-stale').checked});
  if(!enabled.checked||g!==generation)return;
  window.creatureVisionObservation=o;window.creatureVisionReceivedAt=performance.now();window.dispatchEvent(new CustomEvent('creature-vision-observation',{detail:o}));
  trackingTrace.push({at:performance.now(),scenario,observation:o});trackingTrace=trackingTrace.slice(-300);
  scenarioRecords.append(performance.now(),{observation:o,pose:window.creatureDiagnostics?.renderedPose});
  if(scenarioStart===null&&scenarioRecords.current)scenarioRecords.finish('complete',performance.now());
  const target=o.attention_target;
  if(target){window.creatureVisionGaze.distanceInches=target.distance_ft*12;syncGazeControls();}
  if(!performanceRun)hud.textContent='Synthetic visitors · '+o.phase+' · '+(target?.track_id||'no target');
  q('lab-tracking').textContent=`${o.phase} · target ${target?.track_id||'none'} · held ${o.held_track_id||'none'} · pending ${o.pending_track_id||'none'}${window.creatureVisitorLab.emotionalOverride?' · emotion has priority':''}`;
 }catch(e){window.creatureVisionObservation=null;q('lab-tracking').textContent=e.message;}
 if(enabled.checked&&g===generation)setTimeout(()=>poll(g),200);
}
function stop(){
 hud.hidden=true;scenarioRecords.finish('rehearsal-ended',performance.now());epoch++;generation++;scenarioStart=null;performanceRun=null;memoryStory=null;if(memoryTimer!==null)clearTimeout(memoryTimer);memoryTimer=null;if(performanceFrame!==null)cancelAnimationFrame(performanceFrame);performanceFrame=null;window.creatureVisitorLab={active:false};window.creatureVisionObservation=null;
 if(baseline){Object.assign(window.creatureVisionGaze,baseline.gaze);window.creatureSimulation?.setDirection(baseline.direction);document.getElementById('vision-gaze').checked=baseline.gaze.enabled;syncGazeControls();}
 for(const id of managedControls){const e=document.getElementById(id);if(e&&baseline)e.disabled=baseline.disabled[id];}
 const observe=document.getElementById('vision-observe');if(observe&&baseline?.observing){observe.checked=true;observe.dispatchEvent(new Event('change'));}
 q('lab-controls').hidden=true;q('lab-status').textContent='Rehearsal off. Hardware remains disconnected.';baseline=null;
}
enabled.onchange=async()=>{
 if(!enabled.checked){stop();return;}
 if(window.creatureHardware?.enabled||window.creatureHardware?.connecting||window.auditionState?.phase==='connected'){enabled.checked=false;q('lab-status').textContent='End the real encounter and disconnect hardware before rehearsal.';return;}
 epoch++;baseline={gaze:{...window.creatureVisionGaze},direction:window.creatureDiagnostics?.direction||'curious',disabled:{},observing:document.getElementById('vision-observe')?.checked};
 const observe=document.getElementById('vision-observe');if(observe?.checked){observe.checked=false;observe.dispatchEvent(new Event('change'));}
 for(const id of managedControls){const e=document.getElementById(id);if(e){baseline.disabled[id]=e.disabled;e.disabled=true;}}
 window.creatureVisitorLab={active:true,emotion:'curious',emotionalOverride:false};Object.assign(window.creatureVisionGaze,{enabled:true,centerX:.5,centerY:.5+18.5/(2*75*(Math.tan(Math.PI/6)/(1280/720))),gain:.6,invertX:false,invertY:false,cameraBelowInches:18.5,cameraInsetInches:3,distanceInches:72,horizontalFovDegrees:60});document.getElementById('vision-gaze').checked=true;syncGazeControls();trackingTrace=[];
 window.creatureSimulation?.stop();window.creatureSimulation?.setPhase('connecting');
 hud.hidden=false;hud.textContent='Synthetic rehearsal · connecting';q('lab-controls').hidden=false;q('lab-status').textContent='Synthetic rehearsal active · twin only.';
 const g=++generation;
 try{await request('reset_tracking');if(g!==generation)return;poll(g);const value=await request('status');if(g===generation)memoryResult(value);}catch(e){if(g!==generation)return;enabled.checked=false;stop();q('lab-status').textContent=e.message;}
};
function startPerformance(sequence){
 performanceRun={sequence,start:performance.now(),cycle:0};performanceIndex=-1;performanceTrace=[];
 startPerformanceFrames();
 document.querySelector('#encounter-menu').close();
}
function startPerformanceFrames(){
 if(performanceFrame!==null)cancelAnimationFrame(performanceFrame);
 const frame=()=>{performanceFrame=null;if(!enabled.checked||!performanceRun)return;updatePerformance();if(performanceRun)performanceFrame=requestAnimationFrame(frame);};frame();
}
function updatePerformance(){
 if(!performanceRun)return;
 window.creatureVisitorLab.expressionStudy=q('lab-expression-only').checked;
 const beat=performanceProgress(performanceRun.sequence,(performance.now()-performanceRun.start)/1000,q('lab-repeat').checked);
 const seconds=beat.seconds;
 if(beat.cycle!==performanceRun.cycle){performanceRun.cycle=beat.cycle;performanceIndex=-1;}
 window.creatureVisitorLab.performance=beat;
 if(beat.complete){window.creatureVisitorLab.performance=null;performanceRun=null;window.creatureVisitorLab.expressionStudy=false;window.creatureSimulation.setDirection('curious');q('lab-performance').textContent='Silent performance complete.';return;}
 if(beat.index!==performanceIndex){performanceIndex=beat.index;window.creatureSimulation.setDirection(beat.emotion);window.creatureSimulation.setCue(beat.cue);q('lab-emotion').value=beat.emotion;performanceTrace.push({at:seconds,...beat});performanceTrace=performanceTrace.slice(-300);}
 hud.textContent=`Silent study · pass ${beat.cycle+1} · ${beat.emotion} · ${beat.age.toFixed(1)} / ${beat.duration} s`;
 q('lab-performance').textContent=`Silent study · ${beat.emotion} · ${beat.age.toFixed(1)} / ${beat.duration} s`;
}
q('lab-emotion-apply').onclick=()=>{performanceRun={sequence:[[q('lab-emotion').value,3600,'none']],start:performance.now(),cycle:0};performanceIndex=-1;startPerformanceFrames();document.querySelector('#encounter-menu').close();};
q('lab-gauntlet').onclick=()=>startPerformance(EMOTIONAL_GAUNTLET);
q('lab-repair').onclick=()=>startPerformance(REPAIR_STUDY);
q('lab-emotion-stop').onclick=()=>{window.creatureVisitorLab.performance=null;performanceRun=null;window.creatureVisitorLab.expressionStudy=false;window.creatureSimulation.setDirection('curious');q('lab-performance').textContent='Performance stopped.';};
q('lab-run').onclick=async()=>{const g=++generation;try{await request('reset_tracking');if(g!==generation||!enabled.checked)return;scenario=q('lab-scenario').value;scenarioStart=scenario==='manual'?null:performance.now();if(scenarioStart!==null)scenarioRecords.start(scenario,scenarioStart);else scenarioRecords.finish('manual',performance.now());q('lab-status').textContent=scenario==='manual'?'Manual visitor controls active.':'Running '+scenario+' scenario (28 seconds).';poll(g);}catch(e){q('lab-status').textContent=e.message;if(enabled.checked&&g===generation)poll(g);}};
q('lab-pause').onclick=()=>{scenarioRecords.finish('stopped',performance.now());scenarioStart=null;q('lab-status').textContent='Scenario stopped; manual visitors remain active.';};
async function runMemoryStory(){
 if(!memoryStory||!enabled.checked)return;
 const story=memoryStory;
 const elapsed=(performance.now()-story.start)/1000;
 const next=story.spec.actions[story.index];
 if(!next){memoryStory=null;q('lab-memory-beat').textContent='Memory story complete. Review recall provenance and relationship changes below.';return;}
 if(elapsed<next.at){memoryTimer=setTimeout(runMemoryStory,Math.min(200,(next.at-elapsed)*1000));return;}
 if(memoryBusy){memoryTimer=setTimeout(runMemoryStory,100);return;}
 const applied=await memoryAction(next.action,next,true);
 if(memoryStory!==story)return;
 if(!applied){memoryStory=null;q('lab-memory-beat').textContent='Story stopped after a failed action. Review the error before restarting.';return;}
 story.index++;
 q('lab-memory-beat').textContent=`${next.at} s · ${next.action}${next.text?' · '+next.text:''}`;
 memoryTimer=setTimeout(runMemoryStory,100);
}
q('lab-memory-run').onclick=()=>{if(memoryTimer!==null)clearTimeout(memoryTimer);memoryStory={spec:memoryCatalog.scenarios[q('lab-memory-story').value],start:performance.now(),index:0};runMemoryStory();};
q('lab-memory-stop').onclick=()=>{memoryStory=null;if(memoryTimer!==null)clearTimeout(memoryTimer);memoryTimer=null;q('lab-memory-beat').textContent='Story stopped. Complete or discard any open synthetic encounter.';};
async function memoryAction(action,extra={},fromStory=false){
 if(!fromStory){memoryStory=null;if(memoryTimer!==null)clearTimeout(memoryTimer);}
 if(memoryBusy||!enabled.checked)return false;
 memoryBusy=true;panel.querySelectorAll('[data-action],[data-words],#lab-turn').forEach(b=>b.disabled=true);
 const activeEpoch=epoch;
 try{
  const value=await request(action,extra);
  if(activeEpoch!==epoch||!enabled.checked)return false;
  performanceRun=null;window.creatureVisitorLab.performance=null;window.creatureVisitorLab.expressionStudy=false;memoryBusy=false;
  memoryResult(value);q('lab-status').textContent='Rehearsal '+action+' applied.';return true;
 }catch(e){if(activeEpoch===epoch)q('lab-status').textContent=e.message;return false;}
 finally{memoryBusy=false;if(activeEpoch===epoch&&report)memoryResult(report);}
}
panel.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>memoryAction(b.dataset.action,{visitor:q('lab-profile').value,days:14}));
q('lab-turn').onclick=()=>memoryAction('turn',{text:q('lab-text').value});
panel.querySelectorAll('[data-words]').forEach(b=>b.onclick=()=>memoryAction('turn',{text:b.dataset.words}));
q('lab-export').onclick=()=>{if(!report)return;const blob=new Blob([JSON.stringify({kind:'synthetic-rehearsal',memory:report,catalog_version:catalog.version,performance_trace:performanceTrace,tracking:window.creatureVisionObservation,tracking_trace:trackingTrace,scenario_runs:scenarioRecords.snapshot(),pose:window.creatureDiagnostics?.pose},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='visitor-rehearsal.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
