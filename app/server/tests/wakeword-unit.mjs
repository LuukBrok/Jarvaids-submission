import test from "node:test";
import assert from "node:assert/strict";
import { AudioFrames } from "../audio-frames.mjs";
import { WakewordController, WakewordChime } from "../wakeword.mjs";

const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return {promise,resolve}; };
function client() {
  return {batches:[], stops:[], onState:() => () => {},
    async wakewordStart() { return {stream_id:"stream_123",sample_rate:16000,batch_samples:5120,next_sequence:0}; },
    async wakewordStop(id) { this.stops.push(id); },
    async wakewordBatch(id, sequence, base64) {
      this.batches.push({id, sequence, base64});
      return {stream_id:id,sequence,detection:{id:"detected_123"},replayed:false};
    }};
}
function audio(controller, n = 16) { for (let i = 0; i < n; i++) controller.pushFrame(new Float32Array(320).fill(0.5)); }

test("render quanta preserve samples across 320 sample boundaries", () => {
  const frames=[]; const framer=new AudioFrames(frame => frames.push(frame));
  for(let i=0;i<5;i++) framer.push(Float32Array.from({length:128},(_,j)=>i*128+j));
  assert.equal(frames.length,2); assert.equal(frames[0].length,320);
  assert.deepEqual([...frames[0],...frames[1]],Array.from({length:640},(_,i)=>i));
});
test("320 ms batches and detection IDs deliver one callback", async () => {
  const c=client(); let detected=0;
  const controller=new WakewordController(c,{onDetection:()=>detected++});
  await controller.start(); audio(controller); await tick(); audio(controller); await tick();
  assert.equal(c.batches.length,2); assert.equal(Buffer.from(c.batches[0].base64,"base64").length,10240);
  assert.equal(c.batches[1].sequence,1); assert.equal(detected,1); controller.dispose();
});
test("stop suppresses a late detection", async () => {
  const c=client(), pending=deferred(); let detected=0;
  c.wakewordBatch=()=>pending.promise;
  const controller=new WakewordController(c,{onDetection:()=>detected++});
  await controller.start(); audio(controller); controller.stop();
  pending.resolve({stream_id:"stream_123",sequence:0,detection:{id:"late"}}); await tick();
  assert.equal(detected,0); assert.equal(controller.state,"off"); assert.equal(c.stops.length,1);
});
test("one request in flight and queue includes partial samples", async () => {
  const c=client(), pending=deferred(); let calls=0;
  c.wakewordBatch=()=>{calls++;return pending.promise;};
  const controller=new WakewordController(c);
  await controller.start(); audio(controller); audio(controller,50);
  assert.equal(calls,1); assert.equal(controller.state,"waiting");
  audio(controller,1); assert.equal(controller.state,"interrupted");
  assert.equal(controller.queue.length,0); pending.resolve({}); await tick();
});
test("timeout resets without automatic retry", async () => {
  const c=client(); let calls=0;
  c.wakewordBatch=async()=>{calls++;throw Object.assign(new Error(),{code:"timeout"});};
  const controller=new WakewordController(c);
  await controller.start(); audio(controller); await tick(); audio(controller);
  assert.equal(controller.state,"interrupted"); assert.equal(calls,1);
});
test("missing custom model is unavailable, never a fixture detector", async () => {
  const c=client(); c.wakewordStart=async()=>{throw {code:"wakeword_unavailable"};};
  const controller=new WakewordController(c); await controller.start(); audio(controller);
  assert.equal(controller.state,"unavailable"); assert.equal(c.batches.length,0);
});
test("late start response is stopped", async () => {
  const c=client(), pending=deferred(); c.wakewordStart=()=>pending.promise;
  const controller=new WakewordController(c); const started=controller.start(); controller.stop();
  pending.resolve({stream_id:"old"}); await started;
  assert.deepEqual(c.stops,["old"]); assert.equal(controller.streamId,null);
});
test("chime can be unavailable without throwing", async () => {
  const chime=new WakewordChime(); await chime.unlock(); assert.doesNotThrow(()=>chime.play()); chime.dispose();
});
