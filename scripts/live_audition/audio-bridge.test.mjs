import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];

function page(){
  const calls=[],elements=new Map(),sources=[],events=new Map();
  function element(id){
    if(!elements.has(id))elements.set(id,{
      value:id==='#mode'?'elevenlabs':'',disabled:false,style:{},textContent:'',
      addEventListener(){},pause(){},removeAttribute(){},load(){},
    });
    return elements.get(id);
  }
  const context={currentTime:2,destination:{},
    createBuffer(channels,length,rate){return {duration:length/rate,copyToChannel(pcm){calls.push(['pcm',Array.from(pcm)]);}};},
    createBufferSource(){const source={connect(){},start(when){calls.push(['start',when]);},stop(){calls.push(['stop']);}};sources.push(source);return source;},
  };
  class Socket{
    static OPEN=1;
    constructor(){this.readyState=0;this.sent=[];Socket.last=this;}
    send(message){this.sent.push(JSON.parse(message));}
    open(){this.readyState=1;this.onopen();}
    close(){}
  }
  const sandbox=vm.createContext({document:{querySelector:element},
    window:{isSecureContext:true,auditionState:{},addEventListener(name,fn){events.set(name,fn);},creatureSimulation:{
      attachAudio(c){calls.push(['context',c]);},
      schedule(...args){calls.push(['schedule',...args]);},
      stop(){calls.push(['clearMotion']);},setPhase(){},
    }},performance:{now:()=>100},WebSocket:Socket,
    ArrayBuffer,Int16Array,Float32Array,setTimeout:()=>1,clearTimeout(){},clearInterval(){},
    navigator:{mediaDevices:{getUserMedia:async()=>{throw Error('Unexpected microphone request');}}},
    fetch:async()=>{calls.push(['stopRequest']);return {};},
    encodeURIComponent,audioContextFixture:context,
  });
  vm.runInContext(script,sandbox);
  vm.runInContext('audioContext=audioContextFixture;',sandbox);
  return {run:s=>vm.runInContext(s,sandbox),sandbox,calls,sources,Socket,events,element};
}

test('audio startup failure restores retry instead of leaving a disabled CTA',async()=>{
  const p=page();p.run("audioContext.resume=async()=>{throw Error('Audio interrupted');}");
  await p.run('start.onclick()');
  assert.equal(p.element('#start').disabled,false);
  assert.equal(p.sandbox.window.auditionState.phase,'error');
  assert.match(p.element('#status').textContent,/Audio interrupted/);
});

test('insecure phone URL reports HTTPS requirement before requesting microphone',async()=>{
  const p=page();p.sandbox.window.isSecureContext=false;
  await p.run('start.onclick()');
  assert.match(p.element('#status').textContent,/HTTPS/);
  assert.equal(p.element('#start').disabled,false);
});

test('backgrounding an active encounter stops mic, audio, connection and permits reconnect',()=>{
  const p=page();let stopped=0,closed=0;
  p.sandbox.track={stop(){stopped++;}};
  p.sandbox.fixturePeer={close(){closed++;}};
  p.run('ready=true;start.disabled=true;microphone={getTracks:()=>[track]};peer=fixturePeer;document.hidden=true');
  p.events.get('visibilitychange')();
  assert.equal(stopped,1);assert.equal(closed,1);
  assert.equal(p.element('#start').disabled,false);
  assert.equal(p.sandbox.window.auditionState.phase,'ended');
  assert.equal(p.calls.filter(c=>c[0]==='stopRequest').length,1);
});

test('permission sheet is not cancelled; late microphone after navigation is released',async()=>{
  const p=page();let release,stopped=0;
  p.sandbox.navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>{release=resolve;});
  p.sandbox.RTCPeerConnection=class{close(){}};
  p.run('audioContext.resume=async()=>{}');
  const pending=p.run('start.onclick()');await Promise.resolve();await Promise.resolve();
  p.run('document.hidden=true');p.events.get('visibilitychange')();
  assert.equal(p.element('#start').disabled,true);
  p.events.get('pagehide')();
  release({getTracks:()=>[{stop(){stopped++;}}]});await pending;
  assert.equal(stopped,1);assert.equal(p.element('#start').disabled,false);
});

test('actual browser bridge schedules identical PCM and timestamps for sound and jaw',()=>{
  const p=page();
  p.run('playPcm(new Int16Array([0,16384,-16384]).buffer,0)');
  const audio=p.calls.find(c=>c[0]==='start'),motion=p.calls.find(c=>c[0]==='schedule');
  assert.equal(audio[1],2.06);
  assert.equal(motion[3],audio[1]);
  assert.equal(motion[2],44100);
  assert.deepEqual(Array.from(motion[1]),[0,.5,-.5]);
  p.run('playPcm(new Int16Array(4410).buffer,0)');
  const starts=p.calls.filter(c=>c[0]==='start');
  assert.equal(starts[1][1],2.06+3/44100);
});

test('interrupt stops audio and motion, rejects stale audio',()=>{
  const p=page();
  p.run('playPcm(new Int16Array(4410).buffer,0); interruptEleven(); playPcm(new Int16Array(4410).buffer,0);');
  assert.equal(p.calls.filter(c=>c[0]==='start').length,1);
  assert.equal(p.calls.filter(c=>c[0]==='stop').length,1);
  assert.equal(p.calls.filter(c=>c[0]==='clearMotion').length,1);
});

test('server direction is attached to playback of its own audio',()=>{
  const p=page();
  p.run("visitorText='hello friend'; beginSpeech('A short response.');");
  const socket=p.Socket.last;
  socket.open();
  assert.equal(socket.sent[0].visitor_text,'hello friend');
  socket.onmessage({data:JSON.stringify({type:'direction',emotion:'hopeful'})});
  socket.onmessage({data:new Int16Array(4410).buffer});
  assert.equal(p.calls.find(c=>c[0]==='schedule')[4],'hopeful');
  p.run('interruptEleven();');
  socket.onmessage({data:new Int16Array(4410).buffer});
  assert.equal(p.calls.filter(c=>c[0]==='schedule').length,1);
});


test('unexpected socket close without PCM exposes an actionable error',()=>{
  const p=page();p.run("beginSpeech('Speak, Christopher.');");
  p.Socket.last.onclose({code:1008});
  assert.match(p.sandbox.window.auditionState.error,/Voice stream unavailable/);
});

test('intentional interruption does not report a voice-stream failure',()=>{
  const p=page();p.run("beginSpeech('Speak, Christopher.');");
  const socket=p.Socket.last;p.run('interruptEleven();');socket.onclose({code:1000});
  assert.equal(p.sandbox.window.auditionState.error,undefined);
});

test('text arriving after idle end is spoken on a continuation, never sent after end',()=>{
  const p=page();
  const first='I remember the cold mountains and the silence of the forest. ';
  const later='Yet tonight I have found someone willing to listen. ';
  p.run(`appendSpeech(${JSON.stringify(first)}); finishSpeech();`);
  const a=p.Socket.last;a.open();
  p.run(`appendSpeech(${JSON.stringify(later)}); finishSpeech(); finishSpeech();`);
  assert.deepEqual(a.sent.map(m=>m.type),['start','end']);
  a.onmessage({data:new Int16Array(4410).buffer});
  a.onmessage({data:JSON.stringify({type:'done'})});
  const b=p.Socket.last;assert.notEqual(b,a);b.open();
  // The old socket's close must not erase the new one.
  a.onclose({code:1000});
  assert.deepEqual(b.sent.map(m=>m.type),['start','end']);
  b.onmessage({data:new Int16Array(4410).buffer});
  b.onmessage({data:JSON.stringify({type:'done'})});
  const spoken=[...a.sent,...b.sent].filter(m=>m.text).map(m=>m.text).join('');
  assert.equal(spoken,first+later);
  const starts=p.calls.filter(c=>c[0]==='start');
  assert.equal(starts.length,2);assert.equal(starts[1][1],starts[0][1]+.1);
});

test('token fragments are batched on word boundaries without dropping the final tail',()=>{
  const p=page();
  const parts=['I remember the cold mountains and the silence of the for','est. ',
    'Yet tonight I have found some','one willing to lis','ten.'];
  for(const part of parts)p.run(`appendSpeech(${JSON.stringify(part)});`);
  p.run('finishSpeech();');const socket=p.Socket.last;socket.open();
  const chunks=socket.sent.filter(m=>m.text).map(m=>m.text);
  assert.equal(chunks.join(''),parts.join(''));
  for(const chunk of chunks.slice(0,-1))assert.match(chunk,/\s$/);
  assert.ok(chunks.some(c=>c.includes('forest.')));
  assert.ok(chunks.some(c=>c.includes('someone')));
});

test('interruption clears a queued continuation and ignores late done',()=>{
  const p=page();p.run("appendSpeech('I remember the cold mountains and the silence. '); finishSpeech();");
  const socket=p.Socket.last;socket.open();
  p.run("appendSpeech('This continuation must not play.'); finishSpeech(); interruptEleven();");
  socket.onmessage({data:JSON.stringify({type:'done'})});
  assert.equal(p.Socket.last,socket);
  assert.equal(p.run('speechText'),'');
});

test('speech starts after four complete words, with larger continuation batches',()=>{
  const p=page();p.run("appendSpeech('I remember the cold ');");
  const socket=p.Socket.last;assert.ok(socket);socket.open();
  assert.equal(socket.sent[0].text,'I remember the cold ');
  p.run("appendSpeech('mountains and the silence ');");
  assert.equal(socket.sent.length,1);
  p.run("appendSpeech('of the forest.');finishSpeech();");
  assert.equal(socket.sent.filter(m=>m.text).map(m=>m.text).join(''),'I remember the cold mountains and the silence of the forest.');
});
