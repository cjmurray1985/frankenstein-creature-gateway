// Bounded completed-run evidence, independent of ongoing manual polling.
export class RehearsalRecords {
 constructor(){this.current=null;this.completed=[];}
 start(id,now){this.finish('replaced',now);this.current={id,start:now,trace:[]};}
 append(now,data){if(!this.current)return;this.current.trace.push({seconds:(now-this.current.start)/1000,...structuredClone(data)});this.current.trace=this.current.trace.slice(-400);}
 finish(reason,now){if(!this.current)return;this.completed.push({...this.current,finished:now,reason});this.completed=this.completed.slice(-6);this.current=null;}
 snapshot(){return structuredClone({current:this.current,completed:this.completed});}
}
