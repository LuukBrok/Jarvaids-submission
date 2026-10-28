import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {newId, newToken, GenAIClient} from '../client.mjs';

// Plain LAN HTTP can expose getRandomValues without secure-context randomUUID.
Object.defineProperty(globalThis, 'crypto', {configurable:true, value:{
  getRandomValues: buffer => webcrypto.getRandomValues(buffer),
}});
assert.match(newId(), /^[0-9a-f]{32}$/);
assert.notEqual(newId(), newId());
assert.match(newToken(), /^[0-9a-f]{64}$/);
assert.throws(() => new GenAIClient({baseUrl:'http://192.0.2.1:3000'}), TypeError);
const client=new GenAIClient({baseUrl:'http://192.0.2.1:3000',allowLan:true,sessionId:newId(),token:newToken()});
assert.deepEqual(JSON.parse(client.intent('session.pause',{}, {controlSequence:12}).serialized),
  {operation:'session.pause',payload:{},control_sequence:12});
for(const baseUrl of ['http://user:pass@example.com','http://example.com/path','http://example.com?x=1','http://example.com#x']) {
  assert.throws(() => new GenAIClient({baseUrl,allowLan:true}),TypeError);
}
console.log('Client unit checks passed, including LAN crypto and control intent.');
