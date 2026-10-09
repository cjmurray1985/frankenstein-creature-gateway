const clamp=(v,lo=0,hi=1)=>Math.max(lo,Math.min(hi,v));
// Camera-observed first fit, 2026-10-07. Knots are command fractions, not
// encoder readings. Neck angles remain a visual estimate from one camera.
export const TWIN_FIT={
  version:'iphone-20261007-straight-on-pass3',
  neck:{CH1:[-.085,-.04,0,.045,.10],CH2:[.26,.13,0,-.14,-.28],CH3:[.12,.06,0,-.055,-.11]},
  eyes:{CH4:[-.24,-.12,0,.14,.27],CH5:[-.27,-.14,0,.13,.26],CH6:[.28,.14,0,-.13,-.25],CH7:[.27,.14,0,-.13,-.25]},
  eyeHeightScale:1.15,eyeForwardExtra:0,
  lids:[0,.30,.65,1,1],
};
export function fitKnots(value,knots,bipolar=true){
  const fraction=bipolar?(clamp(value,-1,1)+1)/2:clamp(value);
  const at=fraction*4,i=Math.min(3,Math.floor(at));
  return knots[i]+(knots[i+1]-knots[i])*(at-i);
}

