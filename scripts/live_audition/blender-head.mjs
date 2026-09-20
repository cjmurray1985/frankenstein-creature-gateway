import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {clamp} from './motion-core.mjs';
import {eyeContactProjection} from './eye-contact.mjs';

// Fixed eye shells: moving iris/pupil sampling cannot move lids or the orbital outline.
function fitGazeMaterial(mesh,side){
  const material=mesh.material.clone();mesh.material=material;
  const gaze={value:new THREE.Vector2()};
  mesh.geometry.computeBoundingBox();
  const eyeRadius=mesh.geometry.boundingBox.getSize(new THREE.Vector3()).multiplyScalar(.5);
  const eyeCenter=mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
  const localVisitor=new THREE.Vector3();
  // Iris-only centers in the two scan-baked eye maps. The sampled disc excludes lid edges.
  const source={value:new THREE.Vector2(side==='L'?.455:.512,side==='L'?.495:.515)};
  material.onBeforeCompile=shader=>{
    shader.uniforms.creatureGaze=gaze;shader.uniforms.creatureIrisSource=source;
    shader.fragmentShader='uniform vec2 creatureGaze;\nuniform vec2 creatureIrisSource;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`
      #ifdef USE_MAP
        vec2 irisDelta=vMapUv-vec2(0.5)-creatureGaze;
        float irisMask=1.0-smoothstep(0.212,0.223,length(irisDelta));
        // Sample the unoccluded central iris, rather than translating photographed eyelids.
        vec3 irisColor=texture2D(map,creatureIrisSource+irisDelta*0.62).rgb;
        // Muted gray-olive whites keep the narrow opening from glowing;
        // preserve the photographed iris and pupil for readable eye contact.
        vec3 scleraColor=vec3(0.12,0.13,0.10);
        diffuseColor*=vec4(mix(scleraColor,irisColor,irisMask),1.0);
      #endif
    `);
  };
  material.customProgramCacheKey=()=> 'kiri-fixed-shell-iris-v2';
  return {mesh,gaze,restMatrix:mesh.matrix.clone(),set(x,y,cameraPosition){
    // Aim each eye independently at the actual visitor camera after all head
    // transforms. Intersect that optical axis with the fixed ellipsoid, then
    // use the export's planar UV mapping (V runs opposite local Y).
    let baseX=0,baseY=0;
    if(cameraPosition){
      localVisitor.copy(cameraPosition);mesh.worldToLocal(localVisitor);
      // Preserve the signed horizontal camera direction. The old absolute-
      // value shortcut forced the pupils toward opposite targets as the head
      // turned, so one eye could hold contact while the other looked away.
      ({x:baseX,y:baseY}=eyeContactProjection(localVisitor,eyeCenter,eyeRadius));
    }
    // Emotional glances remain offsets from camera contact, not a fixed down-bias.
    gaze.value.set(clamp(baseX+Math.sin(clamp(x,-1,1)*.32)*.5,-.38,.38),clamp(baseY-Math.sin(clamp(y,-1,1)*.24)*.5,-.30,.30));
  }};
}

// Curved upper/lower shells follow each fixed eye surface and meet at a lid seam.
// Added only to the browser derivative: scan anatomy and pupil transforms stay intact.
function buildEyelids(eye,headMeshes){
  eye.geometry.computeBoundingBox();
  const size=eye.geometry.boundingBox.getSize(new THREE.Vector3()).multiplyScalar(.5);
  const ray=new THREE.Raycaster(),forward=new THREE.Vector3(0,0,-1).transformDirection(eye.matrixWorld);
  const texture=headMeshes[0].material.map;
  const canvas=document.createElement('canvas');canvas.width=texture.image.width;canvas.height=texture.image.height;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(texture.image,0,0);
  function skinColor(sign){
    const origin=eye.localToWorld(new THREE.Vector3(0,sign*size.y*.9,size.z+.12));ray.set(origin,forward);
    const hit=ray.intersectObjects(headMeshes,false).find(h=>h.uv);
    if(!hit)return new THREE.Color('#827f46');
    const uv=hit.uv,x=Math.max(0,Math.min(canvas.width-3,Math.round(uv.x*canvas.width))),y=Math.max(0,Math.min(canvas.height-3,Math.round(uv.y*canvas.height)));
    const pixels=ctx.getImageData(x,y,3,3).data,c=[0,0,0];
    for(let i=0;i<pixels.length;i+=4)for(let j=0;j<3;j++)c[j]+=pixels[i+j]/(9*255);
    return new THREE.Color().setRGB(...c,THREE.SRGBColorSpace);
  }
  const lids=[];const nx=48,ny=18,rimRows=3,rows=ny+rimRows;
  for(const sign of [1,-1]){
    const geometry=new THREE.BufferGeometry(),positions=new Float32Array((nx+1)*(rows+1)*3),colors=new Float32Array(positions.length),indices=[];
    const skin=skinColor(sign);
    for(let j=0;j<=rows;j++)for(let i=0;i<=nx;i++){
      const k=j*(nx+1)+i,t=Math.max(0,(j-rimRows)/ny);
      const fold=j<rimRows?.76+.08*j:.98-.12*Math.exp(-(((t-.64)/.075)**2));
      colors.set([skin.r*fold,skin.g*fold,skin.b*fold],k*3);
      if(i<nx&&j<rows){const a=k,b=k+1,c=k+nx+1,d=c+1;indices.push(...(sign>0?[a,b,d,a,d,c]:[a,d,b,a,c,d]));}
    }
    geometry.setAttribute('position',new THREE.BufferAttribute(positions,3).setUsage(THREE.DynamicDrawUsage));
    geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));geometry.setIndex(indices);
    const material=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.74,side:THREE.DoubleSide});
    const mesh=new THREE.Mesh(geometry,material);mesh.name=(sign>0?'Upper':'Lower')+' eyelid '+eye.name;mesh.frustumCulled=false;eye.add(mesh);
    lids.push({geometry,positions,sign});
  }
  canvas.width=canvas.height=1;
  let last=-1;
  return {set(closure){
    closure=clamp(closure);if(Math.abs(closure-last)<.0001)return;last=closure;
    for(const {geometry,positions,sign} of lids){
      for(let j=0;j<=rows;j++)for(let i=0;i<=nx;i++){
        const u=(i/nx*2-1)*.9999,t=Math.max(0,(j-rimRows)/ny),round=Math.sqrt(1-u*u);
        // Upper lid supplies most of the travel; the lower lid rises slightly.
        const seam=-.20*size.y*round;
        const open=sign*(sign>0?.76:.72)*size.y*round;
        const edge=THREE.MathUtils.lerp(open,seam,closure)+(sign>0?-.00012:.00012)*closure;
        let y=THREE.MathUtils.lerp(edge,sign*size.y*round,t);
        // A convex skin pad and recessed fold catch the low laboratory light.
        // Three extra rows turn the free edge inward into a rounded thick rim,
        // rather than ending the lid as a zero-thickness sheet.
        const pad=(sign>0?.13:.08)*size.z*Math.sin(Math.PI*t)*round;
        const crease=.026*size.z*Math.exp(-(((t-.64)/.075)**2))*Math.sin(Math.PI*t)*round;
        const rolled=.040*size.z*Math.exp(-((t/.11)**2))*round;
        let z=size.z*Math.sqrt(Math.max(0,1-u*u-(y/size.y)**2))+.00065+pad-crease+rolled;
        if(j<rimRows){
          const angle=(1-j/rimRows)*Math.PI/2,thickness=.065*size.z*round;
          y+=sign*thickness*(1-Math.cos(angle));
          z-=thickness*Math.sin(angle);
        }
        positions.set([u*size.x,y,z],3*(j*(nx+1)+i));
      }
      geometry.attributes.position.needsUpdate=true;geometry.computeVertexNormals();
    }
  }};
}

// Seal the actual scan aperture, rather than putting a small disc far behind it.
// Weld glTF UV splits only for edge lookup; the source mesh is never changed.
function buildMouthLining(head){
  const geometry=head.geometry,position=geometry.attributes.position,index=geometry.index;
  const morph=geometry.morphAttributes.position[head.morphTargetDictionary.Mouth_Open];
  const welded=new Map(),ids=[],edges=new Map();
  for(let i=0;i<position.count;i++){
    const key=[position.getX(i),position.getY(i),position.getZ(i)].map(v=>Math.round(v*1e6)).join(',');
    if(!welded.has(key))welded.set(key,welded.size);ids.push(welded.get(key));
  }
  for(let i=0;i<index.count;i+=3){
    const triangle=[index.getX(i),index.getX(i+1),index.getX(i+2)];
    for(let e=0;e<3;e++){
      const a=triangle[e],b=triangle[(e+1)%3],key=[ids[a],ids[b]].sort((a,b)=>a-b).join(',');
      if(edges.has(key))edges.get(key).count++;else edges.set(key,{a,b,count:1});
    }
  }
  // Landmark in the exported head's local axes: +Y up, +Z toward the lips.
  const center=new THREE.Vector3(-.029454546,.367272735,.210465193);
  const rim=[...edges.values()].filter(({a,b,count})=>count===1&&
    Math.abs((position.getX(a)+position.getX(b))/2-center.x)<.069&&
    Math.abs((position.getY(a)+position.getY(b))/2-center.y)<.018&&
    (position.getZ(a)+position.getZ(b))/2>.185);
  const degree=new Map();for(const {a,b} of rim)for(const i of [a,b])degree.set(ids[i],(degree.get(ids[i])||0)+1);
  if(!rim.length||[...degree.values()].some(n=>n!==2))throw Error('Mouth lining requires a closed scan aperture');
  const lining=new THREE.BufferGeometry(),vertices=new Float32Array(rim.length*9);
  lining.setAttribute('position',new THREE.BufferAttribute(vertices,3).setUsage(THREE.DynamicDrawUsage));
  // Unlit matte darkness cannot catch the scene's strong face lighting.
  const mesh=new THREE.Mesh(lining,new THREE.MeshBasicMaterial({color:0x030202,side:THREE.DoubleSide,toneMapped:false}));
  mesh.name='Continuous dark mouth lining';mesh.frustumCulled=false;head.add(mesh);
  const point=new THREE.Vector3(),delta=new THREE.Vector3();let last=-1;
  return {edges:rim.length,set(amount){
    if(amount===last)return;last=amount;
    for(let e=0;e<rim.length;e++){
      for(const [j,i] of [rim[e].a,rim[e].b].entries()){
        point.fromBufferAttribute(position,i);delta.fromBufferAttribute(morph,i);
        if(!geometry.morphTargetsRelative)delta.sub(point);
        point.addScaledVector(delta,amount);
        // Tiny overlap behind the lip avoids a visible seam without covering skin.
        point.z-=.00015;point.toArray(vertices,e*9+j*3);
      }
      vertices.set([center.x,center.y-.005-.008*amount,center.z-.035],e*9+6);
    }
    lining.attributes.position.needsUpdate=true;
  }};
}

export async function buildBlenderHead(){
  const gltf=await new GLTFLoader().loadAsync('/assets/creature-kiri.glb');
  const group=new THREE.Group();group.name='KIRI Creature scan';group.add(gltf.scene);
  const mouthMeshes=[];let neck;const shells={};
  gltf.scene.traverse(o=>{
    if(o.userData.web_rig)neck=o;
    if(o.isMesh&&o.morphTargetDictionary?.Mouth_Open!==undefined)mouthMeshes.push(o);
    if(o.isMesh){o.frustumCulled=false;for(const side of ['L','R'])if(o.name.includes('Creature')&&o.name.includes('sclera')&&o.name.endsWith(side))shells[side]=o;}
  });
  if(!neck||!mouthMeshes.length||!shells.L||!shells.R)throw Error('KIRI export is missing its neck, mouth or eye controls');
  const mouthLinings=mouthMeshes.map(buildMouthLining);
  for(const lining of mouthLinings)lining.set(0);
  gltf.scene.traverse(o=>{if(o.name==='Mouth_interior'||o.name==='Mouth interior')o.visible=false;});
  group.updateMatrixWorld(true);
  // Resolve the remaining capture yaw/roll from the actual bilateral eye centers.
  const eyeR=new THREE.Box3().setFromObject(shells.R).getCenter(new THREE.Vector3());
  const eyeL=new THREE.Box3().setFromObject(shells.L).getCenter(new THREE.Vector3());
  const eyeLine=eyeL.clone().sub(eyeR).normalize();
  const level=new THREE.Quaternion().setFromUnitVectors(eyeLine,new THREE.Vector3(1,0,0));
  const pitch=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-8*Math.PI/180);
  gltf.scene.quaternion.premultiply(level).premultiply(pitch);
  group.updateMatrixWorld(true);
  // Bring the eye/lid assembly nearer the scanned orbital rim. Local +Z is
  // forward on these glTF eye meshes; keep the correction independent of gaze.
  const eyeForwardOffset=.0045;
  for(const shell of Object.values(shells))shell.translateZ(eyeForwardOffset);
  group.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(group),center=box.getCenter(new THREE.Vector3());
  const scale=3.7/box.getSize(new THREE.Vector3()).y;
  gltf.scene.position.sub(center);group.scale.setScalar(scale);group.updateMatrixWorld(true);
  // Fade in the head's rest coordinates, so the throat gradient follows neck
  // motion and remains attached when the camera orbits. Opaque black avoids
  // transparency sorting and hides the scanned base silhouette against black.
  for(const mesh of mouthMeshes){
    const material=mesh.material.clone();mesh.material=material;
    const restMatrix=mesh.matrixWorld.clone();
    material.onBeforeCompile=shader=>{
      shader.uniforms.creatureRestMatrix={value:restMatrix};
      shader.vertexShader='uniform mat4 creatureRestMatrix;\nvarying float creatureRestHeight;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ncreatureRestHeight=(creatureRestMatrix*vec4(position,1.0)).y;');
      shader.fragmentShader='varying float creatureRestHeight;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <colorspace_fragment>','#include <colorspace_fragment>\ngl_FragColor.rgb*=smoothstep(-1.55,-0.68,creatureRestHeight);');
    };
    material.customProgramCacheKey=()=> 'kiri-throat-black-fade-v1';
  }
  const eyes={};for(const side of ['L','R'])eyes[side]=fitGazeMaterial(shells[side],side);
  const lids={};for(const side of ['L','R'])lids[side]=buildEyelids(shells[side],mouthMeshes);
  // A shared entrance fade includes eyes/lids as well as skin, without making
  // overlapping scan geometry transparent or altering its throat gradient.
  const entranceReveal={value:1},materials=new Set();
  group.traverse(o=>{if(o.isMesh)for(const m of (Array.isArray(o.material)?o.material:[o.material]))materials.add(m);});
  for(const material of materials){
    const compile=material.onBeforeCompile,cacheKey=material.customProgramCacheKey();
    material.onBeforeCompile=function(shader){
      compile.call(this,shader);shader.uniforms.entranceReveal=entranceReveal;
      shader.fragmentShader='uniform float entranceReveal;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <dithering_fragment>','#include <dithering_fragment>\ngl_FragColor.rgb*=entranceReveal;');
    };
    material.customProgramCacheKey=()=>cacheKey+'-entrance-v1';
  }
  const neckRest=neck.quaternion.clone(),rotation=new THREE.Quaternion();
  const state={asset:'KIRI scan · centered gaze',mouthMeshes:mouthMeshes.length,mouthLiningEdges:mouthLinings.reduce((n,l)=>n+l.edges,0),eyePivots:[],eyeForwardOffset,eyeMode:'iris/pupil only · fixed shells',eyelidsRigged:true,eyelidClosure:0,eyelidPeakClosure:0,mouth:0,restCorrection:{eyeLine:eyeLine.toArray(),pitchDegrees:-8}};
  return {group,state,setReveal(value){entranceReveal.value=clamp(value);},update(p,cameraPosition){
    const amount=clamp(p.M1||0);for(const mesh of mouthMeshes)mesh.morphTargetInfluences[mesh.morphTargetDictionary.Mouth_Open]=amount;
    for(const lining of mouthLinings)lining.set(amount);
    rotation.setFromEuler(new THREE.Euler((p.NECK_FB||0)*.16,(p.NECK_SIDE||0)*.25,-(p.NECK_SIDE||0)*.17,'YXZ'));
    neck.quaternion.copy(neckRest).multiply(rotation);
    group.updateWorldMatrix(true,true);
    eyes.R.set(p.CH7||0,p.CH4||0,cameraPosition);eyes.L.set(p.CH6||0,p.CH5||0,cameraPosition);
    const closure=clamp(p.CH8||0);for(const lid of Object.values(lids))lid.set(closure);state.eyelidClosure=closure;state.eyelidPeakClosure=Math.max(state.eyelidPeakClosure,closure);
    state.mouth=amount;state.neck=[p.NECK_SIDE||0,p.NECK_FB||0];
    state.gaze={R:eyes.R.gaze.value.toArray(),L:eyes.L.gaze.value.toArray()};
    state.eyeShellsFixed=Object.values(eyes).every(e=>e.mesh.matrix.equals(e.restMatrix));
  }};
}
