/**
 * The poll tally's layout (polls.mjs), without a browser.
 *
 *     node --test tests/poll-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { pollModel, pollTally, tallyMark } from "../polls.mjs";

const profile = (id, name) => ({ id, kind: "speaker_profile", data: { name } });
const ballot = (speaker, option) => ({ id: `b-${speaker}`, kind: "poll_ballot", data: { poll_id: "p", speaker_profile_id: speaker, option_id: option } });
const poll = { id: "p", kind: "poll", data: { state: "open", options: [
  { id: "o1", label: "Pizza" }, { id: "o2", label: "Soup" }, { id: "o3", label: "Salad" }] } };
const tally = ballots => pollTally(pollModel({ records: [profile("j", "Julie"), profile("p", "Pieter"), profile("l", "Luuk"), ...ballots] }, poll));

test("each choice is a bar with its letter, count, share and voters", () => {
  const t = tally([ballot("j", "o1"), ballot("p", "o1"), ballot("l", "o3")]);
  assert.deepEqual(t.rows.map(r => [r.letter, r.label, r.count, r.share, r.names]), [
    ["A", "Pizza", 2, 2 / 3, ["Julie", "Pieter"]], ["B", "Soup", 0, 0, []], ["C", "Salad", 1, 1 / 3, ["Luuk"]]]);
});

test("a single top choice is marked, the rest are not", () => {
  const t = tally([ballot("j", "o1"), ballot("p", "o1"), ballot("l", "o3")]);
  assert.equal(t.outcome, "lead");
  assert.deepEqual(t.leaders, ["o1"]);
  assert.deepEqual(t.rows.map(r => r.mark), ["lead", "", ""]);
});

test("a tie is marked as a tie on every tied choice, with no winner", () => {
  const t = tally([ballot("j", "o1"), ballot("p", "o2"), ballot("l", "o3")]);
  assert.equal(t.outcome, "tie");
  assert.deepEqual(t.rows.map(r => r.mark), ["tie", "tie", "tie"]);
  const two = tally([ballot("j", "o1"), ballot("p", "o3")]);
  assert.deepEqual(two.rows.map(r => r.mark), ["tie", "", "tie"]);
});

test("before any vote nothing is marked and every bar is empty", () => {
  const t = tally([]);
  assert.equal(t.outcome, "none");
  assert.deepEqual(t.rows.map(r => [r.mark, r.share]), [["", 0], ["", 0], ["", 0]]);
});

test("a withdrawn ballot counts for nothing", () => {
  const t = tally([ballot("j", "o2"), ballot("p", null)]);
  assert.deepEqual(t.rows.map(r => r.count), [0, 1, 0]);
  assert.equal(t.rows[1].share, 1);
});

test("the mark's words: leading while open, most votes once stopped, a tie always a tie", () => {
  assert.equal(tallyMark("lead", "open"), "Leading");
  assert.equal(tallyMark("lead", "closing"), "Most votes");
  assert.equal(tallyMark("lead", "closed"), "Most votes");
  assert.equal(tallyMark("tie", "open"), "Tie");
  assert.equal(tallyMark("tie", "closed"), "Tie");
  assert.equal(tallyMark("", "closed"), "");
  assert.equal(tallyMark("lead", "cancelled"), "");
});
