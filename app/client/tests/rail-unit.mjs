/**
 * The rail's pure parts: people colours, time formatting, the `jv:quote`
 * detail and the order of a review card's actions.
 *
 *     node --test tests/rail-unit.mjs
 *
 * These are contracts other parts of the client rely on: the quote tool reads
 * the event detail, the threads draw to People rows by colour and id, and the
 * journey presses a card's first primary and first quiet button.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { personIndex, personColour, personInk, clockTime, joinTime } from "../people.mjs";
import { quoteDetail, speakerOf, rowWords } from "../transcript.mjs";
import { cardActions, cardKind, drawnProposed, wasCorrected } from "../review.mjs";
import { sentenceRows } from "../transcript-sentences.mjs";

const snapshot = {
  members: [
    { id: "a_jo", name: "Jo", role: "facilitator" },
    { id: "a_sam", name: "Sam", role: "participant" },
    { id: "a_ali", name: "Ali", role: "participant" },
  ],
  records: [],
};

/** Seconds since 1970 for a local wall-clock time, so the test holds in any
 * time zone: clockTime formats in the device's time. */
const local = (h, m, s = 0) => new Date(2026, 9, 19, h, m, s).getTime() / 1000;

test("a person's colour is their place in join order", () => {
  assert.equal(personIndex(snapshot, "a_jo"), 0);
  assert.equal(personIndex(snapshot, "a_ali"), 2);
  assert.equal(personIndex(snapshot, "nobody"), -1);
  assert.equal(personIndex(snapshot, null), -1);
  assert.equal(personIndex({ records: [] }, "a_jo"), -1, "a snapshot without members has nobody");
  assert.equal(personColour(0), "var(--person-1)");
  assert.equal(personColour(2), "var(--person-3)");
  assert.equal(personColour(9), "var(--person-10)");
  assert.equal(personColour(10), "var(--person-1)", "the eleventh wraps to the first");
  assert.equal(personColour(-1), null);
});

test("a person's name ink is their accent's -deep, in the order of --person-1 to 5", () => {
  assert.deepEqual([0, 1, 2, 3, 4].map(personInk),
    ["var(--lilac-deep)", "var(--mint-deep)", "var(--periwinkle-deep)", "var(--coral-deep)", "var(--yellow-deep)"]);
  assert.equal(personInk(5), "var(--lilac-deep)", "--person-6 is lilac-deep, so its name is too");
  assert.equal(personInk(-1), null);
});

test("times are HH:MM, or HH:MM:SS, with leading zeros, and empty for no time", () => {
  assert.equal(clockTime(local(9, 5, 7)), "09:05");
  assert.equal(clockTime(local(9, 5, 7), { withSeconds: true }), "09:05:07");
  assert.equal(clockTime(local(23, 59, 59), { withSeconds: true }), "23:59:59");
  assert.equal(clockTime(local(0, 0)), "00:00");
  assert.equal(clockTime(null), "");
  assert.equal(clockTime(undefined), "");
  assert.equal(clockTime("not a time"), "");
});

test("the join time is when the person agreed, or 'not yet'", () => {
  assert.equal(joinTime({ agreed_at: local(14, 2) }), "14:02");
  assert.equal(joinTime({ agreed_at: null }), "not yet");
  assert.equal(joinTime({}), "not yet");
});

test("a speaker is the device's member, an unknown voice is nobody, a voice match is a member only by name", () => {
  assert.deepEqual(speakerOf(snapshot, { speaker_actor_id: "a_sam" }), { name: "Sam", actorId: "a_sam", unknown: false });
  assert.deepEqual(speakerOf(snapshot, { attribution: "unidentified", speaker_actor_id: "a_sam" }),
    { name: "Unknown speaker", actorId: null, unknown: true });
  const matched = speakerOf(snapshot, { attribution: "voice_identified", speaker_name: "ali", speaker_actor_id: "a_jo" });
  assert.equal(matched.name, "ali");
  assert.equal(matched.actorId, "a_ali", "the enrolled voice named Ali is the member Ali, not the device's owner");
  assert.equal(speakerOf(snapshot, { attribution: "voice_identified", speaker_name: "Luuk", speaker_actor_id: "a_jo" }).actorId, null);
});

test("the jv:quote detail carries the first segment's id, the words shown, the speaker and the time", () => {
  const common = { status: "final", capture_id: "run", capture_revision: 1, speaker_actor_id: "a_sam",
    duration_ms: 2000, provenance: { synthetic: false } };
  const rows = sentenceRows([
    { id: "seg_1", kind: "transcript_segment", data: { ...common, text: "Hey Jarf Aids", created_at: 100, captured_at_ms: 1000,
      activation_correction: { corrected: true, text: "Hey Jarvaids" } } },
    { id: "seg_2", kind: "transcript_segment", data: { ...common, text: "make a voting list.", created_at: 102, captured_at_ms: 3000 } },
  ]);
  assert.equal(rows.length, 1, "the two fragments are one sentence");
  assert.deepEqual(quoteDetail(snapshot, rows[0]), {
    segmentId: "seg_1",
    text: "Hey Jarvaids make a voting list.",
    speakerName: "Sam",
    speakerActorId: "a_sam",
    createdAt: 100,
  });
  // A single record, as a test or another caller may pass it.
  assert.deepEqual(quoteDetail(snapshot, { id: "seg_9", data: { text: "Plain words.", created_at: 5, attribution: "unidentified" } }),
    { segmentId: "seg_9", text: "Plain words.", speakerName: "Unknown speaker", speakerActorId: null, createdAt: 5 });
  assert.equal(quoteDetail(snapshot, { data: { text: "No id." } }).segmentId, null);
});

test("a stand-in segment never shows a corrected activation phrase", () => {
  assert.equal(rowWords({ text: "raw", provenance: { synthetic: true }, activation_correction: { corrected: true, text: "fixed" } }), "raw");
  assert.equal(rowWords({ text: "raw", activation_correction: { corrected: true, text: "fixed" } }), "fixed");
});

test("a card's actions: Accept first, Correct second, Reject third, for a facilitator", () => {
  assert.deepEqual(cardActions({ facilitator: true, kind: "reading" }), ["accept", "correct", "reject"]);
  assert.deepEqual(cardActions({ facilitator: true, kind: "typed" }), ["accept", "correct", "reject"]);
  assert.deepEqual(cardActions({ facilitator: true, kind: "group" }), ["accept", "correct", "reject"]);
  assert.deepEqual(cardActions({ facilitator: true, kind: "reading", correcting: true }), ["accept", "discard", "reject"],
    "while correcting, Discard takes Correct's place, so Accept and Reject do not move");
  assert.deepEqual(cardActions({ facilitator: true, kind: "canvas" }), ["accept", "reject"],
    "a canvas proposal cannot be edited, so it has no Correct");
  assert.deepEqual(cardActions({ facilitator: false, kind: "reading" }), ["correct"]);
  assert.deepEqual(cardActions({ facilitator: false, kind: "reading", correcting: true }), ["save", "discard"]);
  assert.deepEqual(cardActions({ facilitator: false, kind: "canvas" }), []);
  assert.deepEqual(cardActions({ facilitator: false, kind: "reading", author: false }), [],
    "a participant may correct only what they added: the server refuses anyone else's proposal.edit");
  assert.deepEqual(cardActions({ facilitator: true, kind: "reading", author: false }), ["accept", "correct", "reject"]);
});

test("cards know their kind, whether they are drawn proposed, and whether they were corrected", () => {
  const p = data => ({ id: "p", kind: "proposal", data });
  assert.equal(cardKind(p({ proposal_kind: "canvas", origin: "model" })), "canvas");
  assert.equal(cardKind(p({ proposal_kind: "relationship", form: "cluster", origin: "human" })), "group");
  assert.equal(cardKind(p({ proposal_kind: "content", region_id: "r1", origin: "fixture" })), "reading");
  assert.equal(cardKind(p({ proposal_kind: "content", origin: "human" })), "typed");
  assert.equal(drawnProposed(p({ proposal_kind: "content", origin: "human" })), false, "a person's typed note is not a guess");
  assert.equal(drawnProposed(p({ proposal_kind: "content", region_id: "r1", origin: "fixture" })), true);
  assert.equal(drawnProposed(p({ proposal_kind: "relationship", form: "cluster", origin: "human" })), true);
  assert.equal(wasCorrected(p({ origin: "fixture" })), false);
  assert.equal(wasCorrected(p({ origin: "fixture", last_editor: "a_jo" })), true);
});
