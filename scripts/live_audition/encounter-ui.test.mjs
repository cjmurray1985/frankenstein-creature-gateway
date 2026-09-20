import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
const script=html.match(/<script type="module" id="encounter-ui">([\s\S]*?)<\/script>/)[1];
function fixture(entranceComplete=true){
  const nodes=new Map();
  const document={activeElement:null,querySelector(id){
    if(!nodes.has(id)){
      const handlers=new Map();
      const element={open:false,hidden:false,textContent:'Speak to the Creature',attributes:{},
        addEventListener(type,fn){handlers.set(type,fn);},
        setAttribute(name,value){this.attributes[name]=value;},
        focus(){document.activeElement=this;},
        showModal(){this.open=true;},
        close(){this.open=false;handlers.get('close')?.();},
        click(){handlers.get('click')?.({target:this});},
      };nodes.set(id,element);
    }return nodes.get(id);
  }};
  const window={};vm.runInNewContext(script,{window,document});
  if(entranceComplete)window.encounterUI.setEntranceComplete(true);
  return {ui:window.encounterUI,document,node:id=>document.querySelector(id)};
}
test('start stays visible during connection and hides once engagement begins',()=>{
  const f=fixture(),start=f.node('#start');start.focus();
  f.ui.setPhase('connecting');assert.equal(start.hidden,false);assert.equal(start.textContent,'Connecting…');
  f.ui.setPhase('connected',true);assert.equal(start.hidden,true);assert.equal(f.document.activeElement,f.node('#open-menu'));
  f.ui.setPhase('rendering',true);assert.equal(start.hidden,true);
  f.ui.setPhase('closing',true);assert.equal(start.hidden,true);
  f.ui.reset();assert.equal(start.hidden,false);assert.equal(start.textContent,'Speak to the Creature');
});
test('failed connection exposes feedback and keeps retry available after cleanup',()=>{
  const f=fixture();f.ui.setPhase('error',false);
  assert.equal(f.node('#encounter-menu').open,true);assert.equal(f.node('#start').hidden,false);
  assert.equal(f.document.activeElement,f.node('#close-menu'));
  f.ui.reset();assert.equal(f.node('#start').hidden,false);
});
test('active speech error opens recovery menu without exposing a duplicate start',()=>{
  const f=fixture();f.ui.setPhase('connected',true);f.ui.setPhase('error',true);
  assert.equal(f.node('#encounter-menu').open,true);assert.equal(f.node('#start').hidden,true);
});
test('menu close restores focus and expanded state without changing encounter state',()=>{
  const f=fixture();f.ui.setPhase('connected',true);
  f.node('#open-menu').click();assert.equal(f.node('#encounter-menu').open,true);
  assert.equal(f.node('#open-menu').attributes['aria-expanded'],'true');
  f.node('#close-menu').click();assert.equal(f.node('#encounter-menu').open,false);
  assert.equal(f.node('#open-menu').attributes['aria-expanded'],'false');
  assert.equal(f.document.activeElement,f.node('#open-menu'));assert.equal(f.node('#start').hidden,true);
});

test('CTA waits for actual entrance completion and hides again during replay',()=>{
  const f=fixture(false),start=f.node('#start');
  assert.equal(start.hidden,true);
  f.ui.reset();assert.equal(start.hidden,true);
  f.ui.setPhase('ready');assert.equal(start.hidden,true);
  f.ui.setEntranceComplete(true);assert.equal(start.hidden,false);
  f.ui.setEntranceComplete(false);assert.equal(start.hidden,true);
  f.ui.setEntranceComplete(true);assert.equal(start.hidden,false);
  f.ui.setPhase('connected',true);
  f.ui.setEntranceComplete(true);assert.equal(start.hidden,true);
});
