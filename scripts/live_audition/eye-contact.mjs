import {clamp} from './motion-core.mjs';

// Project a visitor position onto an eye's fixed ellipsoid. The returned
// offsets are texture-space coordinates: U follows local X, while the KIRI
// eye export's V axis runs opposite local Y.
export function eyeContactProjection(visitor,center,radius){
  const x=visitor.x-center.x,y=visitor.y-center.y,z=visitor.z-center.z;
  const denominator=Math.sqrt((x/radius.x)**2+(y/radius.y)**2+(z/radius.z)**2);
  if(!Number.isFinite(denominator)||denominator===0)return {x:0,y:0};
  const hitScale=1/denominator;
  return {
    x:clamp(x*hitScale/(2*radius.x),-.30,.30),
    y:clamp(-y*hitScale/(2*radius.y),-.25,.25),
  };
}

// The theatrical camera sits below the eight-foot Creature. Subtract the
// neutral visitor projection so a frontal head pose reads as direct screen
// contact; subsequent signed deltas still counter-rotate both pupils as the
// head or camera moves.
export function neutralizedEyeContact(contact,neutral){
  return {
    x:clamp(contact.x-neutral.x,-.30,.30),
    y:clamp(contact.y-neutral.y,-.25,.25),
  };
}
