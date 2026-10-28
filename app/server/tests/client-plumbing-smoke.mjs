/** Synthetic two-client journey against the real CLI, including a deliberately lost acknowledgement. */
import assert from 'node:assert/strict';
import {GenAIClient, newId, newToken} from '../client.mjs';
import {SessionConnection} from '../session-sync.mjs';
const baseUrl=process.argv[2], sessionId=newId();
let dropOperation=null, dropped=0;
const owner=new GenAIClient({baseUrl,sessionId,token:newToken(),fetchImpl:async (url,options)=>{
  const response=await fetch(url,options);
  if(options.body && JSON.parse(options.body).operation===dropOperation) {
    await response.text();dropOperation=null;dropped++;
    throw Error('Synthetic acknowledgement lost after committed HTTP response');
  }
  return response;
}});
const guest=new GenAIClient({baseUrl,sessionId,token:newToken()});
const updates=[], attention=[];
const hostSync=new SessionConnection(owner,{pollIntervalMs:100,maxBackoffMs:200,onAttention:e=>attention.push(e)});
const guestSync=new SessionConnection(guest,{pollIntervalMs:100,maxBackoffMs:200,onUpdate:s=>updates.push(s.session.seq)});
const until=async predicate=>{
  const limit=Date.now()+4000;
  while(!predicate()) {if(Date.now()>limit)assert.fail('Timed out waiting for client convergence');await new Promise(r=>setTimeout(r,15));}
};
await owner.create({ownerName:'Synthetic transport owner',title:'Plumbing integration'});
try {
  await owner.submit(owner.intent('consent.acknowledge',{policy_version:1}));
  const invitation=newToken();
  await owner.submit(owner.intent('participant.invite',{invitation,expected_roster_revision:(await owner.snapshot()).session.roster_revision}));
  await guest.join({invitation,name:'Synthetic transport guest',policyVersion:1});
  await owner.submit(owner.intent('session.activate',{policy_version:1,expected_session_revision:(await owner.snapshot()).session.revision}));
  await hostSync.start();await guestSync.start();
  assert.equal(guestSync.snapshot.session.state,'active');
  dropOperation='source.text';
  const intent=owner.intent('source.text',{text:'Synthetic retained note'});
  await assert.rejects(owner.submit(intent),e=>e.outcome==='unknown');
  const result=await owner.submit(intent);
  assert.equal(result.replayed,true);assert.equal(dropped,1);
  await until(()=>guestSync.snapshot?.records.some(r=>r.id===result.result.source.id));
  assert.equal(guestSync.snapshot.records.filter(r=>r.id===result.result.source.id).length,1);
  const accepted=await owner.submit(owner.intent('proposal.review',{proposal_id:result.result.proposal.id,expected_revision:result.result.proposal.revision,decision:'accept'}));
  await until(()=>guestSync.snapshot?.records.some(r=>r.id===accepted.result.item.id));
  const beforeMove=await owner.record(accepted.result.item.id);
  await owner.submit(owner.intent('item.place',{placements:[{id:beforeMove.id,x:120,y:30,expected_position_revision:beforeMove.position?.revision??0}],origin:'human'}));
  await until(()=>guestSync.snapshot?.records.find(r=>r.id===beforeMove.id)?.position?.x===120);
  assert.deepEqual(guestSync.snapshot.board_order,(await owner.snapshot()).board_order);
  guestSync.setOnline(false);
  const second=await owner.submit(owner.intent('source.text',{text:'Synthetic offline interval'}));
  guestSync.setOnline(true);
  await until(()=>guestSync.snapshot?.records.some(r=>r.id===second.result.source.id));
  dropOperation='session.heartbeat';
  await assert.rejects(hostSync.submitControl('session.heartbeat'),e=>e.outcome==='unknown');
  const retained=hostSync.pendingControl.intent;
  const replay=await hostSync.retryPendingControl();
  assert.equal(replay.intent,retained);assert.equal(replay.result.replayed,true);
  assert.equal(hostSync.pendingControl,null);
  await hostSync.pause();
  await until(()=>guestSync.snapshot?.session.state==='paused');
  guestSync.setVisibility(false);guestSync.setVisibility(true);
  await until(()=>guestSync.snapshot?.session.state==='paused');
  assert.equal((await owner.snapshot()).session.state,'paused');
  assert.ok(['ready','not_ready'].includes((await owner.readiness()).status));
  assert.ok(await owner.diagnostics());
  // A second device revokes this participant while it is polling.
  const snapshot=await owner.snapshot();
  await owner.submit(owner.intent('participant.remove',{actor_id:guestSync.snapshot.actor_id,expected_roster_revision:snapshot.session.roster_revision},{controlSequence:snapshot.next_control_sequence}));
  await until(()=>guest.state==='revoked');
  assert.equal(guestSync.snapshot,null);
  assert.ok(updates.length>=2);
  assert.ok(attention.some(e=>e.code==='control_uncertain'));
  console.log('PASS: real HTTP two-client delta/reconnect, lost write acknowledgement, exact control retry, pause, diagnostics and revocation.');
} finally {
  hostSync.dispose();guestSync.dispose();
  if(owner.state==='active') await owner.delete();
  owner.dispose();guest.dispose();
}
