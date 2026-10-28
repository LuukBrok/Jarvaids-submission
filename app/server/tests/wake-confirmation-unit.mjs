import test from 'node:test';
import assert from 'node:assert/strict';
import { WakeConfirmation } from '../../client/wake-confirmation.mjs';
const record=(id,changes={})=>({id,kind:'transcript_segment',data:{status:'final',text:'Hey Jarvaids',
  provenance:{synthetic:false},voice_command:{phrase:'Hey Jarvaids',status:'incomplete'},...changes}});
test('only a new spoken activation rings once across repeated polling',()=>{
  const heard=[],gate=new WakeConfirmation(r=>heard.push(r.id));
  gate.begin({records:[record('old')]});
  const snapshot={records:[record('old'),record('new')]};
  gate.update(snapshot,true);gate.update(snapshot,true);assert.deepEqual(heard,['new']);
});
test('quiet results, typed commands, synthetic ASR and continuations never ring',()=>{
  const heard=[],gate=new WakeConfirmation(r=>heard.push(r.id));gate.begin({records:[]});
  gate.update({records:[record('quiet',{voice_command:null}),record('typed',{input_method:'typed'}),
    record('fixture',{provenance:{synthetic:true}}),record('continued',{voice_command:{phrase:'Hey Jarvaids',activation_segment_id:'earlier'}})]},true);
  assert.deepEqual(heard,[]);
});
test('a stopped microphone cannot ring from a delayed transcription',()=>{
  const heard=[],gate=new WakeConfirmation(r=>heard.push(r.id));gate.begin({records:[]});
  gate.update({records:[record('late')]},false);gate.update({records:[record('late')]},true);
  assert.deepEqual(heard,[]);
});
