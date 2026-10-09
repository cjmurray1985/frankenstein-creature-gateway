// Silent, synthetic performance beats. No dialogue or inferred visitor emotion.
export const EMOTIONAL_GAUNTLET=Object.freeze([
 ['curious',4,'none'],['attentive',4,'listening'],['hopeful',4,'think'],['engaged',4,'agree'],
 ['wary',4,'none'],['suspicious',4,'suspicion'],['startled',3,'startle'],
 ['hurt',4,'none'],['vulnerable',4,'plead'],['angry',4,'disagree'],
 ['relieved',4,'relief'],['withdrawn',4,'withdraw'],['dormant',4,'none'],['curious',4,'none'],
]);
export const REPAIR_STUDY=Object.freeze([
 ['curious',3,'listening'],['suspicious',2,'suspicion'],['hurt',3,'none'],
 ['vulnerable',3,'plead'],['relieved',3,'relief'],['hopeful',3,'none'],['curious',3,'none'],
]);
export function performanceBeat(sequence,seconds){
 let start=0;
 for(let index=0;index<sequence.length;index++){
  const [emotion,duration,cue]=sequence[index];
  if(seconds<start+duration)return {index,emotion,cue,age:Math.max(0,seconds-start),duration,complete:false};
  start+=duration;
 }
 return {index:sequence.length,emotion:'curious',cue:'none',age:0,duration:0,complete:true};
}
export const performanceDuration=sequence=>sequence.reduce((sum,beat)=>sum+beat[1],0);
export function performanceProgress(sequence,elapsedSeconds,repeat=false){
 const duration=performanceDuration(sequence);
 if(!Number.isFinite(elapsedSeconds)||!Number.isFinite(duration)||duration<=0)throw new TypeError('Finite positive performance clock required');
 const elapsed=Math.max(0,elapsedSeconds),cycle=repeat?Math.floor(elapsed/duration):0;
 const seconds=repeat?elapsed%duration:elapsed;
 return {...performanceBeat(sequence,seconds),cycle,seconds,totalDuration:duration};
}
