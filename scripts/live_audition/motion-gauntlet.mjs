// Local animation/recorded-ElevenLabs integration review. No provider sessions.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const {chromium}=createRequire(import.meta.url)('playwright');
const out=path.resolve('analysis/animation-gauntlet',process.argv[2]||'motion-review');
await fs.mkdir(out);
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
const page=await browser.newPage({viewport:{width:1180,height:1024},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://localhost:8767/');await page.waitForFunction(()=>window.creatureDiagnostics?.ready);
await page.click('#motion-study');
await page.waitForTimeout(800);
assert.ok((await page.evaluate(()=>window.creatureDiagnostics.pose.M1))>.05);
// Starting actual reference audio must take over from the movement study.
await page.click('#preview');
await page.waitForFunction(()=>document.querySelector('#reference').currentTime>.1);
assert.equal(await page.locator('#motion-study').textContent(),'Run movement study');
const recordingInfo=await page.evaluate(()=>{
 const audio=document.querySelector('#reference'),canvas=document.querySelector('#creature-stage canvas');
 const video=canvas.captureStream(24),sound=audio.captureStream();
 const stream=new MediaStream([...video.getVideoTracks(),...sound.getAudioTracks()]);
 const mime=MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')?'video/webm;codecs=vp9,opus':'video/webm';
 const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2200000});
 const chunks=[],samples=[];let sampling=true;
 const sample=()=>{if(!sampling)return;samples.push({t:audio.currentTime,wall:performance.now(),...window.creatureDiagnostics.pose,speaking:window.creatureDiagnostics.speaking});requestAnimationFrame(sample);};
 recorder.ondataavailable=e=>chunks.push(e.data);recorder.start();sample();
 window.finishReview=()=>new Promise(resolve=>{sampling=false;recorder.onstop=async()=>{
  const bytes=new Uint8Array(await new Blob(chunks,{type:mime}).arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  stream.getTracks().forEach(t=>t.stop());resolve({base64:btoa(binary),samples});
 };recorder.stop();});
 return {referenceStart:audio.currentTime,audioTracks:stream.getAudioTracks().length,mime};
});
await page.waitForTimeout(8000);
const {base64,samples}=await page.evaluate(()=>window.finishReview());
await fs.writeFile(path.join(out,'reference-playback.webm'),Buffer.from(base64,'base64'));
await page.locator('#creature-stage canvas').screenshot({path:path.join(out,'reference-speaking.png')});
await page.click('#preview');await page.waitForTimeout(400);
const paused=await page.evaluate(()=>({...window.creatureDiagnostics.pose}));
assert.equal(paused.M1,0);
assert.ok(samples.some(s=>s.M1>.5)&&samples.some(s=>s.M1<.02),'Mouth must articulate and close in speech gaps');
assert.ok(samples.every(s=>Number.isFinite(s.M1)&&s.M1>=0&&s.M1<=1));
assert.equal(recordingInfo.audioTracks,1,'Review video should contain the reference sound');
// Switching from audible reference to study must pause the sound and keep the
// study running after the asynchronous media pause handler.
await page.click('#preview');await page.waitForTimeout(350);
await page.click('#motion-study');await page.waitForTimeout(500);
assert.ok(await page.evaluate(()=>document.querySelector('#reference').paused));
assert.equal(await page.locator('#motion-study').textContent(),'Stop movement study');
// Exercise the two neck axes through their full study and verify stopping it.
await page.waitForTimeout(5650);
const lateral=await page.evaluate(()=>({...window.creatureDiagnostics.pose}));assert.ok(Math.abs(lateral.NECK_SIDE)>.25);
await page.waitForTimeout(4000);
const pitch=await page.evaluate(()=>({...window.creatureDiagnostics.pose}));assert.ok(Math.abs(pitch.NECK_FB)>.25);
await page.click('#motion-study');await page.waitForTimeout(200);
assert.equal(await page.locator('#motion-study').textContent(),'Run movement study');
await page.locator('#creature-stage canvas').screenshot({path:path.join(out,'after-stop.png')});
const intervals=samples.slice(1).map((s,i)=>s.wall-samples[i].wall).sort((a,b)=>a-b);
const result={errors,recordingInfo,frameSamples:samples.length,medianFrameMs:intervals[Math.floor(intervals.length/2)],maxMouth:Math.max(...samples.map(s=>s.M1)),minMouth:Math.min(...samples.map(s=>s.M1)),paused,lateral,pitch,samples};
await fs.writeFile(path.join(out,'results.json'),JSON.stringify(result,null,2));
await browser.close();assert.equal(errors.length,0);console.log(JSON.stringify({...result,samples:undefined}));
