// Real browser continuity is independent of synthetic rehearsal profiles.
const token=document.querySelector('meta[name="hardware-token"]')?.content;
const menu=document.querySelector('#encounter-menu');
if(token&&menu){
  const panel=document.createElement('details');panel.id='encounter-memory';
  panel.innerHTML='<summary>Encounter memory</summary><p>This browser automatically remembers recent visitor statements, names you share, and the relationship between visits. No name is required. Memory lasts up to one year after your last visit; audio is not saved.</p><p class="fine">Return recognition uses this browser, not a camera match. Synthetic rehearsal profiles are separate.</p><p id="memory-status" role="status" aria-live="polite">Checking encounter memory…</p><button id="memory-forget" class="secondary" type="button">Forget me</button><p class="fine">Forget me clears this browser’s stored encounter memory and ends its active conversation.</p>';
  menu.querySelector('.menu-content')?.append(panel);
  if(!panel.isConnected)menu.append(panel);
  const status=panel.querySelector('#memory-status'),forget=panel.querySelector('#memory-forget');
  let busy=false,sequence=0;
  async function request(body){
    const response=await fetch('/visitor-memory',body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,...body}),signal:AbortSignal.timeout(10000)}:{signal:AbortSignal.timeout(5000)});
    let result;try{result=await response.json();}catch{throw Error('Encounter memory is unavailable.');}
    if(!response.ok)throw Error((typeof result.error==='string'?result.error:result.error?.message)||'Encounter memory is unavailable.');
    return result;
  }
  async function refresh(){
    if(busy)return;
    const revision=++sequence;
    try{
      const result=await request();if(revision!==sequence||busy)return;
      status.textContent=result.save_error?'The latest statement could not be saved. Previous memory is preserved.':result.returning?`Returning browser · ${result.encounters} encounter${result.encounters===1?'':'s'} remembered · ${result.remembered_facts} explicit fact${result.remembered_facts===1?'':'s'}.`:'New browser history · memory will begin when you speak and the Creature starts replying.';
    }catch(error){if(revision===sequence&&!busy)status.textContent=error.message;}
  }
  forget.addEventListener('click',async()=>{
    if(busy)return;busy=true;sequence++;forget.disabled=true;status.textContent='Clearing encounter memory…';
    window.dispatchEvent(new Event('creature-memory-forget'));
    try{
      await request({action:'forget'});
      status.textContent='Your stored encounter memory has been cleared. The next encounter starts fresh.';
    }catch(error){status.textContent='Could not confirm deletion: '+error.message+' You can try again.';}
    finally{busy=false;forget.disabled=false;}
  });
  panel.addEventListener('toggle',()=>{if(panel.open)refresh();});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  setInterval(()=>{if(!document.hidden&&panel.open)refresh();},5000);
  refresh();
}
