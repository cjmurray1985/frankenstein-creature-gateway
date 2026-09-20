import * as THREE from './vendor/three.module.js';
import {clamp} from './motion-core.mjs';

// Pixel landmarks are traced from camch4hd01, t=2.000 s, 1920×1080.
// World depth is an authored estimate. Frontal x/y and the surface come from evidence.
export const LANDMARKS={
  crown:[835,18],chin:[925,806],neck:[915,978],
  eyes:[[823,418],[1040,428]],nose:[928,538],mouth:[921,674],
};
export const OUTLINE=[[18,823,846],[21,810,883],[24,796,921],[27,788,944],[30,782,961],[33,775,978],[36,770,993],[39,767,1005],[42,764,1017],[45,762,1030],[48,759,1042],[50,757,1050],[53,753,1060],[56,750,1070],[59,746,1081],[62,743,1091],[65,739,1101],[68,737,1108],[71,735,1116],[74,732,1123],[77,730,1131],[80,728,1138],[83,725,1143],[86,723,1147],[89,720,1152],[92,718,1156],[95,715,1161],[98,714,1165],[101,712,1169],[104,711,1172],[107,709,1176],[110,708,1180],[113,707,1182],[116,707,1185],[119,706,1187],[122,706,1190],[125,705,1192],[128,705,1195],[131,704,1197],[134,704,1199],[137,704,1200],[140,704,1202],[143,704,1203],[146,704,1204],[149,701,1205],[152,700,1206],[155,698,1206],[158,696,1208],[161,695,1209],[164,693,1211],[167,691,1212],[170,691,1214],[173,689,1215],[176,687,1216],[179,685,1217],[182,685,1218],[185,683,1218],[188,683,1219],[191,683,1219],[194,681,1219],[197,681,1220],[200,679,1220],[203,678,1220],[206,676,1221],[209,675,1221],[212,674,1221],[215,674,1222],[218,673,1222],[221,672,1223],[224,671,1223],[227,671,1223],[230,670,1224],[233,669,1224],[236,668,1224],[239,665,1224],[242,665,1224],[245,665,1224],[248,665,1223],[251,665,1223],[254,665,1223],[257,665,1223],[260,664,1223],[263,664,1222],[266,664,1222],[269,663,1222],[272,663,1222],[275,663,1221],[278,661,1221],[281,661,1221],[284,661,1221],[287,661,1220],[290,661,1219],[293,661,1218],[296,661,1217],[299,660,1217],[302,660,1216],[305,660,1215],[308,661,1214],[311,660,1213],[314,661,1212],[317,661,1212],[320,660,1211],[323,660,1210],[326,660,1209],[329,660,1208],[332,660,1207],[335,660,1207],[338,660,1206],[341,660,1205],[344,660,1204],[347,661,1203],[350,662,1203],[353,663,1202],[356,663,1201],[359,663,1200],[362,663,1199],[365,664,1199],[368,665,1198],[371,665,1197],[374,665,1196],[377,665,1196],[380,663,1195],[383,663,1194],[386,662,1193],[389,662,1193],[392,662,1192],[395,662,1192],[398,662,1191],[401,662,1191],[404,662,1190],[407,663,1190],[410,664,1190],[413,665,1189],[416,666,1189],[419,666,1188],[422,667,1188],[425,668,1187],[428,669,1187],[431,669,1186],[434,670,1186],[437,671,1186],[440,673,1187],[443,673,1187],[446,674,1187],[449,676,1187],[452,677,1186],[455,677,1185],[458,677,1185],[461,677,1185],[464,678,1186],[467,678,1187],[470,679,1187],[473,679,1187],[476,679,1187],[479,680,1187],[482,680,1187],[485,681,1186],[488,682,1186],[491,683,1186],[494,684,1186],[497,685,1186],[500,686,1186],[503,686,1184],[506,687,1183],[509,688,1182],[512,689,1180],[515,690,1179],[518,691,1178],[521,691,1176],[524,692,1175],[527,693,1173],[530,695,1171],[533,696,1170],[536,698,1168],[539,699,1166],[542,701,1164],[545,702,1162],[548,703,1158],[551,705,1156],[554,706,1155],[557,708,1155],[560,711,1151],[563,712,1149],[566,712,1148],[569,713,1146],[572,714,1144],[575,714,1142],[578,715,1141],[581,716,1139],[584,716,1137],[587,717,1135],[590,718,1134],[593,718,1132],[596,719,1130],[599,720,1128],[602,720,1127],[605,721,1125],[608,722,1123],[611,722,1122],[614,723,1120],[617,723,1119],[620,724,1117],[623,725,1115],[626,725,1114],[629,726,1112],[632,726,1111],[635,727,1109],[638,728,1107],[641,728,1106],[644,729,1104],[647,729,1103],[650,730,1101],[653,730,1101],[656,731,1100],[659,731,1100],[662,732,1099],[665,732,1099],[668,733,1098],[671,733,1098],[674,734,1097],[677,734,1097],[680,735,1096],[683,735,1096],[686,736,1095],[689,736,1095],[692,737,1094],[695,737,1094],[698,738,1093],[701,738,1093],[704,738,1093],[707,739,1092],[710,739,1092],[713,740,1092],[716,740,1091],[719,740,1091],[722,741,1091],[725,741,1090],[728,741,1090],[731,742,1090],[734,742,1090],[737,742,1089],[740,743,1089],[743,743,1089],[746,744,1088],[749,744,1088],[752,744,1088],[755,744,1087],[758,745,1087],[761,745,1086],[764,745,1085],[767,746,1085],[770,746,1084],[773,746,1084],[776,747,1083],[779,747,1083],[782,747,1082],[785,748,1082],[788,748,1081],[791,748,1081],[794,748,1080],[797,749,1080],[800,749,1079],[803,749,1079],[806,749,1078],[809,750,1078],[812,750,1077],[815,750,1077],[818,750,1076],[821,751,1076],[824,751,1076],[827,751,1075],[830,751,1075],[833,752,1074],[836,752,1074],[839,752,1074],[842,752,1073],[845,753,1073],[848,753,1072],[851,753,1072],[854,753,1071],[857,753,1071],[860,754,1070],[863,754,1069],[866,754,1069],[869,754,1068],[872,754,1068],[875,754,1067],[878,755,1066],[881,755,1066],[884,755,1065],[887,755,1065],[890,755,1064],[893,756,1063],[896,756,1063],[899,756,1062],[902,756,1061],[905,757,1060],[908,757,1060],[911,758,1059],[914,758,1058],[917,759,1057],[920,759,1056],[923,760,1055],[926,760,1054],[929,766,1053],[932,772,1052],[935,777,1051],[938,783,1050],[941,786,1048],[944,790,1046],[947,794,1044],[950,797,1042],[953,800,1040],[956,804,1038],[959,813,1031],[962,821,1024],[965,830,1017],[968,839,1010],[971,847,1003],[974,856,996]];
export const EYES=[{x:822,y:418,rx:53,ry:23,tilt:-.055},{x:1038,y:427,rx:51,ry:24,tilt:.16}];
export const world=(x,y,z=0)=>[(x-930)/250,(500-y)/250,z];
export function bounds(y){
  for(let i=1;i<OUTLINE.length;i++)if(y<=OUTLINE[i][0]){
    const a=OUTLINE[i-1],b=OUTLINE[i],t=clamp((y-a[0])/(b[0]-a[0]));
    return [a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
  }
  return OUTLINE.at(-1).slice(1);
}
const backDepth=y=>{const [l,r]=bounds(y);return 1.08*clamp((y-8)/160)*Math.min(1,(r-l)/560);};
const gauss=(x,y,cx,cy,sx,sy)=>Math.exp(-(((x-cx)/sx)**2+((y-cy)/sy)**2));
export function depth(x,y){
  const [l,r]=bounds(y),q=(x-(l+r)/2)/((r-l)/2);
  let z=.10+.72*Math.min(1,(r-l)/500)*Math.sqrt(Math.max(0,1-q*q))*clamp((y-10)/150);
  z+=.37*gauss(x,y,939,471,40,100)+.24*gauss(x,y,928,540,42,31);
  z+=.10*gauss(x,y,925,632,112,56)+.10*gauss(x,y,925,767,117,70);
  z-=.15*gauss(x,y,921,674,83,16);
  for(const e of EYES){
    z-=.15*gauss(x,y,e.x,e.y,63,42);
    z+=.12*gauss(x,y,e.x,e.y-49,73,24);
    z+=.09*gauss(x,y,e.x,e.y+77,55,44);
  }
  return z;
}
export function mouthOffset(x,y,open){
  // Continuous local skin deformation. No jaw group, cut seam or chin rotation.
  // Authored aperture ~2–40 px at 195 px mouth width. The rigid chin stays fixed.
  const u=(x-921)/100;
  if(Math.abs(u)>=1||y<590||y>805)return 0;
  const w=(1-u*u)**.65;
  const top=663+3*u,bottom=top+21*w;
  const delta=(2+38*clamp(open)-21)*w;
  if(y<top)return -.15*delta*Math.exp(-(((y-top)/28)**2));
  if(y>bottom){
    const fall=Math.exp(-(((y-bottom)/43)**2))*clamp((805-y)/35);
    return .85*delta*fall;
  }
  return delta*((y-top)/Math.max(1,bottom-top)-.15);
}
const eyeNorm=(x,y,e)=>{
  const dx=x-e.x,dy=y-e.y-e.tilt*dx;
  return (dx/e.rx)**2+(dy/e.ry)**2;
};

export async function buildPhotoHead(){
  const texture=await new THREE.TextureLoader().loadAsync('/assets/head-reference.png');
  texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=8;
  const group=new THREE.Group();
  const skin=new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide});
  // One connected front surface from crown to neck. Photo UVs retain actual asymmetry.
  const cols=200,rows=330,vertices=[],uv=[],pixels=[],indices=[];
  for(let j=0;j<=rows;j++){
    const y=18+(974-18)*j/rows,[l,r]=bounds(y);
    for(let i=0;i<=cols;i++){
      const x=l+(r-l)*i/cols;
      vertices.push(...world(x,y,depth(x,y)));uv.push(x/1920,1-y/1080);pixels.push(x,y);
    }
  }
  const add=(a,b,c)=>{
    const x=(pixels[2*a]+pixels[2*b]+pixels[2*c])/3,y=(pixels[2*a+1]+pixels[2*b+1]+pixels[2*c+1])/3;
    if(!EYES.some(e=>eyeNorm(x,y,e)<.97))indices.push(a,b,c);
  };
  for(let j=0;j<rows;j++)for(let i=0;i<cols;i++){
    const a=j*(cols+1)+i,b=a+cols+1;
    add(a,b,a+1);add(a+1,b,b+1);
  }
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
  geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geometry.setIndex(indices);geometry.computeVertexNormals();
  const face=new THREE.Mesh(geometry,skin);group.add(face);
  const base=Float32Array.from(vertices);
  const mouthIndices=[];
  for(let i=0;i<pixels.length/2;i++)if(Math.abs(pixels[2*i]-921)<101&&pixels[2*i+1]>590&&pixels[2*i+1]<805)mouthIndices.push(i);

  // Back volume closes the object. It is deliberately plain where no scan exists.
  const backVerts=[],backColors=[],backIndices=[];
  const imageCanvas=document.createElement('canvas');imageCanvas.width=1920;imageCanvas.height=1080;
  const imageContext=imageCanvas.getContext('2d',{willReadFrequently:true});imageContext.drawImage(texture.image,0,0);
  const imagePixels=imageContext.getImageData(0,0,1920,1080).data;
  const colorAt=(x,y)=>{
    const n=(Math.round(y)*1920+Math.round(x))*4;
    return new THREE.Color(imagePixels[n]/255,imagePixels[n+1]/255,imagePixels[n+2]/255).convertSRGBToLinear();
  };
  const bc=80,br=150;
  for(let j=0;j<=br;j++){
    const y=18+956*j/br,[l,r]=bounds(y);
    for(let i=0;i<=bc;i++){
      const angle=i/bc*Math.PI,weight=Math.sin(angle),x=(l+r)/2+(r-l)/2*Math.cos(angle);
      backVerts.push(...world(x,y,.1-backDepth(y)*weight));
      // Sample inside the subject, never extend edge pixels from the room into
      // the unphotographed back. Hair uses a known interior lock of real hair.
      const hair=colorAt(685+5*Math.sin(angle*2),280+clamp((y-50)/560)*60);
      const skinColor=colorAt(i<bc/2?r-35:l+35,y);
      const color=hair.lerp(skinColor,clamp((y-550)/100));
      const interior=new THREE.Color(0x24271e).lerp(new THREE.Color(0x7d8955),clamp((y-550)/100));
      color.lerp(interior,Math.min(1,weight*6));
      backColors.push(color.r,color.g,color.b);
      if(j<br&&i<bc){const a=j*(bc+1)+i,b=a+bc+1;backIndices.push(a,a+1,b,a+1,b+1,b);}
    }
  }
  const bg=new THREE.BufferGeometry();bg.setAttribute('position',new THREE.Float32BufferAttribute(backVerts,3));
  bg.setAttribute('color',new THREE.Float32BufferAttribute(backColors,3));bg.setIndex(backIndices);bg.computeVertexNormals();
  group.add(new THREE.Mesh(bg,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.95,side:THREE.DoubleSide})));

  // Closed, gently crowned scalp. Its boundary is shared with both head surfaces.
  // Depth and hair on the unseen crown are authored, not reconstructed measurements.
  for(const y of [18,974]){
    const [l,r]=bounds(y),boundary=[];
    for(let i=0;i<=cols;i++){const x=l+(r-l)*i/cols;boundary.push(world(x,y,depth(x,y)));}
    for(let i=1;i<bc;i++){const a=i/bc*Math.PI;boundary.push(world((l+r)/2+(r-l)/2*Math.cos(a),y,.1-backDepth(y)*Math.sin(a)));}
    const center=world((l+r)/2,y,-.08),rings=16,n=boundary.length,v=[],c=[],ii=[];
    for(let j=0;j<=rings;j++)for(let i=0;i<n;i++){
      const t=j/rings,b=boundary[i],lift=y===18?.01*(1-t*t):0;
      v.push(center[0]+(b[0]-center[0])*t,center[1]+lift,center[2]+(b[2]-center[2])*t);
      const grain=.90+.10*Math.sin(i*1.31+j*2.73);
      const shade=new THREE.Color(y===18?0x292b24:0x899461).multiplyScalar(grain);c.push(shade.r,shade.g,shade.b);
      if(j<rings){const a=j*n+i,k=j*n+(i+1)%n;ii.push(a,k,a+n,k,k+n,a+n);}
    }
    const cap=new THREE.BufferGeometry();cap.setAttribute('position',new THREE.Float32BufferAttribute(v,3));cap.setAttribute('color',new THREE.Float32BufferAttribute(c,3));cap.setIndex(ii);cap.computeVertexNormals();
    const material=y===18?new THREE.MeshStandardMaterial({vertexColors:true,roughness:.85,side:THREE.DoubleSide}):new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide});
    group.add(new THREE.Mesh(cap,material));
  }

  const eyes=[],lids=[];
  for(const e of EYES){
    const ev=[],euv=[],ei=[],resolution=40;
    for(let j=0;j<=resolution;j++)for(let i=0;i<=resolution;i++){
      const x=e.x+(i/resolution*2-1)*e.rx*1.12,y=e.y+(j/resolution*2-1)*e.ry*1.3;
      ev.push(...world(x,y,depth(x,y)-.014));euv.push(x/1920,1-y/1080);
      if(j<resolution&&i<resolution){const a=j*(resolution+1)+i,b=a+resolution+1;ei.push(a,b,a+1,a+1,b,b+1);}
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(ev,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(euv,2));g.setIndex(ei);
    const eye=new THREE.Mesh(g,skin);group.add(eye);eyes.push({geometry:g,uv:Float32Array.from(euv),landmark:e});
    // Sliding upper skin lid. Iris remains behind it, never squashed with the skin.
    const lv=[],luv=[],li=[],lx=64,ly=12;
    for(let j=0;j<=ly;j++)for(let i=0;i<=lx;i++){
      const u=i/lx*2-1,w=Math.sqrt(Math.max(0,1-u*u)),x=e.x+e.rx*u;
      const top=e.y+e.tilt*(x-e.x)-e.ry*w;
      lv.push(...world(x,top,depth(x,top)+.012));
      luv.push(x/1920,1-(e.y-e.ry-22+j/ly*6)/1080);
      if(j<ly&&i<lx){const a=j*(lx+1)+i,b=a+lx+1;li.push(a,b,a+1,a+1,b,b+1);}
    }
    const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.Float32BufferAttribute(lv,3));lg.setAttribute('uv',new THREE.Float32BufferAttribute(luv,2));lg.setIndex(li);
    const lid=new THREE.Mesh(lg,skin);group.add(lid);lids.push({geometry:lg,landmark:e,lx,ly});
  }
  // The actual cylindrical neck-bolt proportions, with the neck kept continuous.
  const metal=new THREE.MeshStandardMaterial({color:0xa1a8a7,metalness:.85,roughness:.3});
  for(const [x,y] of [[716,726],[1109,735]]){
    const bolt=new THREE.Mesh(new THREE.CylinderGeometry(.048,.048,.18,28),metal);
    bolt.rotation.z=Math.PI/2;bolt.position.set(...world(x,y,.12));group.add(bolt);
    const cap=new THREE.Mesh(new THREE.CylinderGeometry(.064,.064,.025,24),metal);
    cap.rotation.z=Math.PI/2;cap.position.copy(bolt.position);cap.position.x+=(x<930?-.09:.09);group.add(cap);
  }
  let previousOpen=-1,previousLids=-1;
  function update(p){
    if(Math.abs(p.M1-previousOpen)>.0001){
      const pos=geometry.attributes.position;
      for(const i of mouthIndices)pos.setY(i,base[3*i+1]-mouthOffset(pixels[2*i],pixels[2*i+1],p.M1)/250);
      pos.needsUpdate=true;previousOpen=p.M1;
    }
    eyes.forEach(({geometry:g,uv:rest},i)=>{
      const dx=(i===0?p.CH7:p.CH6)*14,dy=(i===0?p.CH4:p.CH5)*12;
      const uv=g.attributes.uv;
      for(let k=0;k<uv.count;k++)uv.setXY(k,rest[k*2]-dx/1920,rest[k*2+1]+dy/1080);
      uv.needsUpdate=true;
    });
    // Reference has naturally lowered lids; CH8=0 is the photographed opening.
    const closure=clamp((p.CH8-.18)/.82);
    if(Math.abs(closure-previousLids)>.0001){
      for(const {geometry:g,landmark:e,lx,ly} of lids){
        const pos=g.attributes.position;
        for(let j=0;j<=ly;j++)for(let i=0;i<=lx;i++){
          const u=i/lx*2-1,w=Math.sqrt(Math.max(0,1-u*u)),x=e.x+e.rx*u;
          const top=e.y+e.tilt*(x-e.x)-e.ry*w;
          const y=top+j/ly*2*e.ry*w*closure;
          pos.setXYZ(j*(lx+1)+i,...world(x,y,depth(x,y)+.015));
        }
        pos.needsUpdate=true;
      }
      previousLids=closure;
    }
  }
  update({M1:0,CH4:0,CH5:0,CH6:0,CH7:0,CH8:.18});
  return {group,update,geometry,landmarks:LANDMARKS,pixels,mouthIndices};
}
