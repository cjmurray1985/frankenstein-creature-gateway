// Deterministic data-only scenarios. Identical catalog is consumed by Python replay.
export function sampleScenario(spec, seconds) {
  const active = windows => (windows || []).some(([start,end]) => seconds >= start && seconds < end);
  const people = [];
  for (const track of spec.tracks) {
    if (!active(track.visible)) continue;
    let point = track.keys[0].slice(1);
    for (let i=1;i<track.keys.length;i++) {
      const before=track.keys[i-1], after=track.keys[i];
      if(seconds>=after[0]) point=after.slice(1);
      else {const u=Math.max(0,(seconds-before[0])/(after[0]-before[0]));point=before.slice(1).map((v,j)=>v+(after[j+1]-v)*u);break;}
    }
    people.push({track_id:track.id,x:point[0],y:point[1],distance_ft:point[2]});
  }
  return {people,stale:active(spec.stale)};
}
