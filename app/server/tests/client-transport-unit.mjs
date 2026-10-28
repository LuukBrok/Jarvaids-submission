import assert from 'node:assert/strict';
import test from 'node:test';
import {GenAIClient, RequestError, ApiError, newId, newToken} from '../client.mjs';
const json = (value, status=200) => new Response(JSON.stringify(value), {status, headers:{'Content-Type':'application/json'}});
const client = fetchImpl => new GenAIClient({sessionId:newId(), token:newToken(), fetchImpl});
const error = (code, outcome) => e => e instanceof RequestError && e.code === code && e.outcome === outcome;
const bounded = async promise => { let timer; try { return await Promise.race([promise,new Promise((_resolve,reject)=>{timer=setTimeout(()=>reject(new Error('Expected client deadline did not fire')),150);})]); } finally {clearTimeout(timer);} };
const deferred = () => { let resolve; const promise=new Promise(r=>resolve=r); return {promise,resolve}; };

test('exact retained bytes and request ID survive an uncertain retry', async () => {
  const calls=[];
  const c=client(async (_url, options) => {calls.push(options); if(calls.length===1) throw new Error('private network details'); return json({replayed:true});});
  const payload={text:'before'};
  const intent=c.intent('source.text',payload); payload.text='after';
  await assert.rejects(c.submit(intent), error('network_error','unknown'));
  assert.equal(calls.length,1);
  assert.equal((await c.submit(intent)).replayed,true);
  assert.equal(calls[0].body,intent.serialized);
  assert.equal(calls[1].body,calls[0].body);
  assert.equal(calls[1].headers['X-Request-ID'],calls[0].headers['X-Request-ID']);
  assert.equal(JSON.parse(calls[1].body).payload.text,'before');
  assert.equal(calls[1].credentials,'omit'); assert.equal(calls[1].redirect,'error');
  assert.equal(Object.isFrozen(intent),true);
});
test('foreign and reconstructed intents cannot dispatch', () => {
  let sent=0; const c=client(()=>{sent++;return json({});}); const other=client(()=>json({}));
  const intent=other.intent('session.pause');
  assert.throws(()=>c.submit(intent),TypeError);
  assert.throws(()=>other.submit({...intent}),TypeError);
  assert.equal(sent,0);
});
test('nonfinite payload and invalid deadline are rejected before dispatch', () => {
  const c=client(()=>assert.fail('dispatch'));
  assert.throws(()=>c.intent('x',{n:Infinity}),TypeError);
  assert.throws(()=>c.intent('x',{n:1n}),TypeError);
  assert.throws(()=>c.intent('x',{}, {controlSequence:-1}),TypeError);
  assert.throws(()=>new GenAIClient({timeoutMs:0}),TypeError);
});
test('pre-aborted request is not sent', async () => {
  let sent=0; const c=client(()=>{sent++; return json({});});
  const controller=new AbortController(); controller.abort();
  await assert.rejects(c.submit(c.intent('source.text'),{signal:controller.signal}),error('aborted','not_sent'));
  assert.equal(sent,0);
});
test('timeout covers fetch and body decoding with no automatic retry', async () => {
  let calls=0;
  const c=client(async ()=>{calls++;return {ok:true,status:200,json:()=>new Promise(()=>{})};});
  await assert.rejects(bounded(c.submit(c.intent('source.text'),{timeoutMs:15})),error('timeout','unknown'));
  assert.equal(calls,1);
  const hanging=client(()=>new Promise(()=>{}));
  await assert.rejects(hanging.snapshot({timeoutMs:15}),error('timeout','unknown'));
});
test('inflight cancellation is uncertain and suppresses late success', async () => {
  const response=deferred(); let signal;
  const c=client((_url,options)=>{signal=options.signal;return response.promise;});
  const controller=new AbortController();
  const pending=c.submit(c.intent('source.text'),{signal:controller.signal}); controller.abort();
  await assert.rejects(pending,error('aborted','unknown'));
  assert.equal(signal.aborted,true); response.resolve(json({secret:'late'}));
  assert.equal(c.state,'active');
});
test('malformed successful write response retains uncertainty', async () => {
  const c=client(()=>new Response('not JSON'));
  await assert.rejects(c.submit(c.intent('x')), error('invalid_response','unknown'));
});
test('authenticated rejection revokes all requests and owned URLs', async () => {
  const slow=deferred(); let calls=0;
  const c=client(()=>++calls===1 ? slow.promise : json({error:{code:'unauthorised'}},401));
  const states=[];c.onState(s=>states.push(s));c.onState(()=>{throw Error('observer');});
  const url=c.createMediaUrl(new Blob(['private']));
  const pending=c.snapshot({timeoutMs:25}); const caught=assert.rejects(pending,error('client_inactive','unknown'));
  await assert.rejects(c.snapshot(),e=>e instanceof ApiError && e.status===401);
  await caught;
  assert.equal(c.state,'revoked');assert.deepEqual(states,['revoked']);
  await assert.rejects(fetch(url));
  await assert.rejects(c.snapshot(),error('client_inactive','not_sent'));
  assert.throws(()=>c.intent('x'),error('client_inactive','not_sent'));
  slow.resolve(json({secret:'late'}));
  assert.equal(calls,2);
});
test('401 revocation does not wait for an unreadable error body', async () => {
  const c=client(()=>({status:401,ok:false,json:()=>new Promise(()=>{})}));
  const pending=c.snapshot({timeoutMs:15});
  await assert.rejects(pending,error('timeout','response_received'));
  assert.equal(c.state,'revoked');
});
test('invitation rejection and missing media do not revoke credentials', async () => {
  const calls=[];const c=client((_url,options)=>{calls.push(options);return json({error:{code:calls.length===1?'invalid_invitation':'media_unavailable'}},calls.length===1?401:410);});
  await assert.rejects(c.join({invitation:'invalid',name:'fixture',policyVersion:1}),ApiError);
  assert.equal(c.state,'active');assert.equal(calls[0].headers.Authorization,undefined);
  await assert.rejects(c.media('x'),ApiError);assert.equal(c.state,'active');
});
test('session expiry and deletion are terminal', async () => {
  for(const [code,state] of [['session_expired','expired'],['session_deleted','deleted']]) {
    const c=client(()=>json({error:{code}},410));
    await assert.rejects(c.snapshot(),ApiError);assert.equal(c.state,state);
    await assert.rejects(c.snapshot(),error('client_inactive','not_sent'));
  }
  const c=client(()=>json({state:'deleted'}));
  assert.deepEqual(await c.delete(),{state:'deleted'});assert.equal(c.state,'deleted');
});
test('dispose cancels writes and prevents new media URLs or requests', async () => {
  const response=deferred();const c=client(()=>response.promise);
  const url=c.createMediaUrl(new Blob(['private']));
  const pending=c.submit(c.intent('x'),{timeoutMs:25});c.dispose();c.dispose();
  await assert.rejects(pending,error('client_inactive','unknown'));
  await assert.rejects(fetch(url));
  assert.throws(()=>c.createMediaUrl(new Blob()),error('client_inactive','not_sent'));
  await assert.rejects(c.snapshot(),error('client_inactive','not_sent'));
  response.resolve(json({secret:'late'}));
});
test('media URL ownership is bounded and explicit release frees capacity', () => {
  const c=client(()=>json({}));const urls=Array.from({length:16},()=>c.createMediaUrl(new Blob()));
  assert.throws(()=>c.createMediaUrl(new Blob()),RangeError);
  c.revokeMediaUrl(urls[0]);c.createMediaUrl(new Blob());c.dispose();
});
test('readiness preserves not-ready diagnostics without bearer credentials', async () => {
  const calls=[];const c=client((url,options)=>{calls.push({url,options});return json({status:'not_ready',checks:{store:'busy'}},503);});
  let result; await assert.doesNotReject(async()=>{result=await c.readiness();});
  assert.equal(result.status,'not_ready');
  assert.equal(calls[0].options.headers.Authorization,undefined);assert.match(calls[0].url,/\/ready$/);
});
test('server failure and expired control replay keep uncertain outcome', async () => {
  for(const [status,code] of [[500,'internal_error'],[409,'control_replay_expired']]) {
    const c=client(()=>json({error:{code}},status));
    await assert.rejects(c.submit(c.intent('session.pause',{}, {controlSequence:1})),e=>e instanceof ApiError && e.outcome==='unknown');
  }
});

test('a successful facilitator deletion receipt clears client authority', async () => {
  const sid=newId();
  const c=new GenAIClient({sessionId:sid,token:newToken(),fetchImpl:()=>json({state:'deleted',content_available:false,session_id:sid})});
  assert.equal((await c.snapshot()).state,'deleted');assert.equal(c.state,'deleted');
});
