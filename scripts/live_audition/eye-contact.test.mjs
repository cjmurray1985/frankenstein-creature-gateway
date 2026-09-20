import test from 'node:test';
import assert from 'node:assert/strict';
import {eyeContactProjection,neutralizedEyeContact} from './eye-contact.mjs';

const center={x:0,y:0,z:0},radius={x:.04,y:.026,z:.022};

test('the two eyes converge on a centered visitor instead of diverging',()=>{
  const anatomicalRight=eyeContactProjection({x:.08,y:-.10,z:3},center,radius);
  const anatomicalLeft=eyeContactProjection({x:-.08,y:-.10,z:3},center,radius);
  assert.ok(anatomicalRight.x>0);
  assert.ok(anatomicalLeft.x<0);
  assert.ok(Math.abs(anatomicalRight.x+anatomicalLeft.x)<1e-12);
  assert.ok(anatomicalRight.y>0&&anatomicalLeft.y>0);
});

test('signed camera motion moves both pupils toward the same visitor',()=>{
  const rightBefore=eyeContactProjection({x:.08,y:0,z:3},center,radius).x;
  const leftBefore=eyeContactProjection({x:-.08,y:0,z:3},center,radius).x;
  const rightAfter=eyeContactProjection({x:.22,y:0,z:3},center,radius).x;
  const leftAfter=eyeContactProjection({x:.06,y:0,z:3},center,radius).x;
  assert.ok(rightAfter>rightBefore);
  assert.ok(leftAfter>leftBefore);
});

test('projection is measured from the actual geometry center',()=>{
  const offsetCenter={x:4,y:-2,z:1};
  const shifted=eyeContactProjection({x:4.08,y:-2.10,z:4},offsetCenter,radius);
  const origin=eyeContactProjection({x:.08,y:-.10,z:3},center,radius);
  assert.ok(Math.abs(shifted.x-origin.x)<1e-12);
  assert.ok(Math.abs(shifted.y-origin.y)<1e-12);
});

test('neutral calibration centers the pupils but preserves matching head compensation',()=>{
  const neutralRight={x:.0405,y:.0687},neutralLeft={x:.0219,y:.0712};
  assert.deepEqual(neutralizedEyeContact(neutralRight,neutralRight),{x:0,y:0});
  assert.deepEqual(neutralizedEyeContact(neutralLeft,neutralLeft),{x:0,y:0});
  const turnedRight=neutralizedEyeContact({x:-.0038,y:.0647},neutralRight);
  const turnedLeft=neutralizedEyeContact({x:-.0252,y:.0667},neutralLeft);
  assert.ok(Math.abs(turnedRight.x-turnedLeft.x)<.003);
  assert.ok(Math.abs(turnedRight.y-turnedLeft.y)<.002);
  assert.ok(turnedRight.x<0&&turnedLeft.x<0);
});
