import test from "node:test";
import assert from "node:assert/strict";
import { sentenceRows } from "../../client/transcript-sentences.mjs";
const part = (text, time, extra = {}) => ({id: String(time), data: {
  text, capture_id: "run", capture_revision: 1, captured_at_ms: time,
  duration_ms: 2000, attribution: "voice_identified", speaker_actor_id: "mic",
  speaker_profile_id: "voice1", speaker_name: "Luuk", provenance: {synthetic:false}, ...extra
}});
test("join unfinished fragments until punctuation without changing source evidence", () => {
  const sources = [part("If you could try this out", 1000), part("with a full sentence.", 3000), part("Next sentence.", 5000)];
  const before = JSON.stringify(sources);
  const rows = sentenceRows(sources);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].data.text, "If you could try this out with a full sentence.");
  assert.deepEqual(rows[0].segment_ids, ["1000", "3000"]);
  assert.equal(JSON.stringify(sources), before);
});
test("speaker changes, capture changes and long pauses begin a new row", () => {
  for (const extra of [{speaker_profile_id:"voice2"}, {attribution:"unidentified"},
    {capture_id:"other"}, {capture_revision:2}, {captured_at_ms:20000}, {provenance:{synthetic:true}}]) {
    assert.equal(sentenceRows([part("Unfinished",1000), part("new words.",3000,extra)]).length,2);
  }
});
test("ellipsis is unfinished and canonical wake phrase and command metadata survive joining", () => {
  const rows = sentenceRows([part("Hey Jarf Aids...",1000,{activation_correction:{corrected:true,text:"Hey Jarvaids..."}}),
    part("Make a voting list.",3000,{voice_command:{intent:"voting"}})]);
  assert.equal(rows.length,1);
  assert.equal(rows[0].data.activation_correction.text,"Hey Jarvaids... Make a voting list.");
  assert.equal(rows[0].data.text,"Hey Jarf Aids... Make a voting list.");
  assert.equal(rows[0].data.voice_command.intent,"voting");
});
