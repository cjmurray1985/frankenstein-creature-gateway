// Run: NODE_PATH=<runtime node_modules> node scripts/live_audition/visual-gauntlet.mjs <pass-name>
// Local renderer only. Never starts a provider session or operates the physical head.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const {chromium}=createRequire(import.meta.url)('playwright');
const pass=process.argv[2]||'review';
if(!/^[a-z0-9-]+$/.test(pass))throw Error('Use a simple new pass name');
const out=path.resolve('analysis/animation-gauntlet',pass);
await fs.mkdir(out); // Preserve previous passes instead of silently replacing evidence.
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://localhost:8767/');
await page.waitForFunction(()=>window.creatureDiagnostics?.ready);
const cases=[
  ['front-rest',{}],['mouth-half',{M1:.5}],['mouth-open',{M1:1}],
  ['blink-half',{CH8:.6}],['blink-closed',{CH8:1}],
  ['gaze-left',{CH6:-.8,CH7:-.8}],['gaze-right',{CH6:.8,CH7:.8}],
  ['neck-left',{NECK_SIDE:-.85}],['neck-right',{NECK_SIDE:.85}],
  ['neck-forward',{NECK_FB:.85}],['neck-back',{NECK_FB:-.85}],
  ['three-quarter',{},[.50,.10]],['three-quarter-mouth',{M1:1},[-.50,0]],
  ['combined-left',{M1:1,NECK_SIDE:-1,NECK_FB:1,CH8:.6},[-.4,.1]],
  ['combined-right',{M1:.75,NECK_SIDE:1,NECK_FB:-1},[.4,-.1]],
  ['turned-blink',{CH8:1,NECK_SIDE:.5},[.4,0]],
];
const results=[];
for(const [name,pose,camera] of cases){
  await page.evaluate(({pose,camera})=>{window.creatureReview.reset();window.creatureReview.setPose(pose);if(camera)window.creatureReview.camera(...camera);},{pose,camera});
  await page.waitForTimeout(180);
  await page.locator('#creature-stage canvas').screenshot({path:path.join(out,name+'.png')});
  results.push({name,pose,diagnostics:await page.evaluate(()=>({...window.creatureDiagnostics,landmarks:window.creatureReview.landmarks()}))});
}
await page.evaluate(()=>{window.creatureReview.reset();window.creatureReview.setPose({});});
await page.screenshot({path:path.join(out,'page.png'),fullPage:true});
await page.setViewportSize({width:390,height:844});
await page.waitForTimeout(180);
await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
await fs.writeFile(path.join(out,'results.json'),JSON.stringify({errors,mobileOverflow:overflow,results},null,2));
await browser.close();
console.log(JSON.stringify({pass,cases:results.length,errors,mobileOverflow:overflow,out}));
if(errors.length||overflow)process.exitCode=1;
