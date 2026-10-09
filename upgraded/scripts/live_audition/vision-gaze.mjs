import {TWIN_FIT,fitKnots} from './twin-fit.mjs';
// Provisional camera-to-gaze target, shared by twin and connected rig.
export function visionGazeTarget(observation,settings,now,receivedAt,neckPose={}){
 const neutral={CH1:0,CH2:0,CH3:0,CH4:0,CH5:0,CH6:0,CH7:0};
 if(observation?.fresh!==true||!Number.isFinite(now)||!Number.isFinite(receivedAt)||!Number.isFinite(observation.expires_after_ms)||observation.expires_after_ms<=0||now<receivedAt||now-receivedAt>=Math.min(1000,observation.expires_after_ms)||!observation.attention_target)return {pose:neutral,tracking:false};
 const target=observation.attention_target;
 // Prefer facial mesh center; otherwise upper fifth of person box is a head hint.
 const face=(Array.isArray(observation.facial_cues)?observation.facial_cues:[]).find(f=>f&&f.person_track_id===target.track_id&&f.bbox_xyxy);
 const b=face?.bbox_xyxy??target.bbox_xyxy;
 if(!Array.isArray(b)||b.length!==4||b.some(v=>!Number.isFinite(v)||v<0||v>1)||b[2]<=b[0]||b[3]<=b[1])return {pose:neutral,tracking:false};
 settings=settings??{};
 const numeric=(key,fallback,min,max)=>Number.isFinite(settings[key])?Math.max(min,Math.min(max,settings[key])):fallback;
 const gain=numeric('gain',.6,.2,1),centerX=numeric('centerX',.5,-1,2),centerY=numeric('centerY',.5,-1,2);
 const point=[(b[0]+b[2])/2,face?(b[1]+b[3])/2:b[1]+.2*(b[3]-b[1])];
 const clamp=v=>Math.max(-.65,Math.min(.65,v));
 // Translate a provisional camera ray from chest-camera origin to eye origin.
 // Range is a user estimate, never inferred monocular distance.
 const depth=numeric('distanceInches',60,12,240),inset=numeric('cameraInsetInches',3,0,12);
 const halfH=Math.tan(numeric('horizontalFovDegrees',60,30,120)*Math.PI/360),halfV=halfH/(1280/720);
 const scale=(depth+inset)/depth;
 const x=clamp((point[0]-centerX)*2*scale*gain)*(settings.invertX?-1:1);
 const y=clamp(((centerY-point[1])*2*scale-numeric('cameraBelowInches',18.5,0,48)/(depth*halfV))*gain)*(settings.invertY?-1:1);
 // Use the existing visually fitted neck geometry to aim the face. These
 // angles are estimates, not measured joint feedback or exact inverse kinematics.
 const yaw=Math.atan(x*halfH),pitch=Math.atan(y*halfV);
 const inverse=(angle,knots)=>{
  for(let i=0;i<4;i++)if(angle>=Math.min(knots[i],knots[i+1])&&angle<=Math.max(knots[i],knots[i+1]))return clamp(-1+i*.5+.5*(angle-knots[i])/(knots[i+1]-knots[i]));
  return clamp(Math.abs(angle-knots[0])<Math.abs(angle-knots[4])?-1:1);
 };
 const neck={CH1:inverse(-pitch,TWIN_FIT.neck.CH1),CH2:inverse(yaw,TWIN_FIT.neck.CH2),CH3:x*.15};
 // Compensate against the eased commanded neck, so eyes acquire immediately
 // then relax as the head catches up. No assumption of instantaneous head motion.
 const neckValue=id=>Number.isFinite(neckPose[id])?neckPose[id]:0;
 const headYaw=fitKnots(neckValue('CH2'),TWIN_FIT.neck.CH2);
 const headPitch=-fitKnots(neckValue('CH1'),TWIN_FIT.neck.CH1);
 const headRoll=fitKnots(neckValue('CH3'),TWIN_FIT.neck.CH3);
 const dx=yaw-headYaw,dy=pitch-headPitch;
 const localX=dx*Math.cos(headRoll)+dy*Math.sin(headRoll);
 const localY=dy*Math.cos(headRoll)-dx*Math.sin(headRoll);
 // Eye angular spans are provisional; fitted pupil UV travel is not an encoder.
 const eyeX=clamp(localX/.48),eyeY=clamp(localY/.38);
 return {tracking:true,point,trackId:target.track_id,source:face?'facial center':'upper-person estimate',pose:{...neck,CH4:eyeY,CH5:eyeY,CH6:-eyeX,CH7:-eyeX}};
}
