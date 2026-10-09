// Recorded retrofit command profile. Rest is the 50% semantic anchor.
// These are commanded travel limits, not verified mechanical stop margins.
export const SERVO_PROFILE_VERSION='retrofit-20261007';
export const SERVO_PROFILE=Object.freeze(Object.fromEntries(Object.entries({
 CH1:[1000,1492,2000,0],CH2:[1000,1492,2000,3],CH3:[1000,1492,2000,5],
 CH4:[1200,1492,1800,7],CH5:[1200,1492,1800,8],CH6:[1200,1492,1800,11],
 CH7:[1200,1492,1800,13],CH8:[1600,1897,2100,15],
}).map(([id,values])=>[id,Object.freeze(values)])));
