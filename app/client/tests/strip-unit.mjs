/**
 * The session strip's pure parts (tools/strip.mjs): which records are
 * moments and when, the time axis, what is after a moment, the words for a
 * moment, and stepping with the keys.
 *
 *     node --test tests/strip-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { QUOTE_LINKS_KEY, MIN_SPAN, afterMoment, axisFrom, commandWords, fractionOf, momentLabel, momentsFrom,
  readQuoteLinks, step, timeAt } from "../tools/strip.mjs";

const T = 1_800_000_000;   // a fixed moment, in seconds
const clock = s => `t+${s - T}`;   // deterministic, unlike the local time zone

const SNAPSHOT = {
  records: [
    { id: "photo-1", kind: "source", data: { type: "image", created_at: T + 10 } },
    { id: "typed-src", kind: "source", data: { type: "text", text: "x", created_at: T + 11 } },
    { id: "n1", kind: "item", data: { item_kind: "content", status: "accepted", text: "Onboarding loses people", created_at: T + 60 } },
    { id: "n-undone", kind: "item", data: { item_kind: "content", status: "undone", text: "Gone", created_at: T + 70 } },
    { id: "cluster", kind: "item", data: { item_kind: "relationship", form: "cluster", status: "accepted", text: "G", created_at: T + 80 } },
    { id: "photo-2", kind: "source", data: { type: "image", created_at: T + 200 } },
    { id: "n2", kind: "item", data: { item_kind: "content", status: "accepted", text: "Too many fields before value", created_at: T + 300, proposal_id: "p-quote" } },
    { id: "pen", kind: "item", data: { item_kind: "stroke", status: "accepted", made_by_hand: true, created_at: T + 350 } },
    { id: "seg-cmd", kind: "transcript_segment", data: { status: "final", text: "Hey Jarvaids, make a summary",
      voice_command: { status: "recognised", intent: "summary" }, created_at: T + 400 } },
    { id: "seg-todo", kind: "transcript_segment", data: { status: "final", text: "to-do",
      voice_command: { status: "recognised", intent: "todo" }, created_at: T + 410 } },
    { id: "seg-fixture", kind: "transcript_segment", data: { status: "final", text: "stand-in", provenance: { synthetic: true },
      voice_command: { status: "recognised", intent: "summary" }, created_at: T + 420 } },
    { id: "seg-unfinished", kind: "transcript_segment", data: { status: "final", voice_command: { status: "incomplete" }, created_at: T + 430 } },
    { id: "p1", kind: "proposal", data: { proposal_kind: "content", status: "needs_review", origin: "model", text: "Run a test", created_at: T + 450 } },
    { id: "n3", kind: "item", data: { item_kind: "content", status: "accepted", text: "People skip the tour", created_at: T + 500 } },
    { id: "no-time", kind: "item", data: { item_kind: "content", status: "accepted", text: "Fixture note" } },
  ],
};

test("moments: photographs, accepts and recognised commands, oldest first", () => {
  const moments = momentsFrom(SNAPSHOT);
  assert.deepEqual(moments.map(m => m.key), ["photo:photo-1", "accept:n1", "photo:photo-2", "accept:n2", "command:seg-cmd",
    "command:seg-todo", "accept:n3"]);
  assert.deepEqual(moments.map(m => m.time - T), [10, 60, 200, 300, 400, 410, 500]);
  assert.equal(moments[1].text, "Onboarding loses people");
  assert.equal(moments[4].words, "summary");
  assert.equal(moments[5].words, "to-do list", "the transcript's own name for the command");
});

test("moments: a text source, an undone item, a group, a stroke, a stand-in or unfinished command and a record with no time are not moments", () => {
  const keys = momentsFrom(SNAPSHOT).map(m => m.key);
  for (const id of ["typed-src", "n-undone", "cluster", "pen", "seg-fixture", "seg-unfinished", "no-time", "p1"]) {
    assert.ok(!keys.some(k => k.endsWith(`:${id}`)), id);
  }
  assert.deepEqual(momentsFrom(null), []);
  assert.deepEqual(momentsFrom({}), []);
});

test("moments: a quote is placed at its note's time, found by the note's id or the proposal it came from", () => {
  const snap = { records: [...SNAPSHOT.records,
    { id: "p-quoted", kind: "proposal", data: { proposal_kind: "content", status: "needs_review", origin: "human", created_at: T + 120 } }] };
  const links = {
    "p-quoted": { segmentId: "s1", time: T + 5 },        // the note's own time wins over the link's
    "p-quote": { segmentId: "s2", time: T + 6 },         // now accepted as n2: found through proposal_id
    "elsewhere": { segmentId: "s3", time: (T + 250) * 1000 },   // not in this snapshot: the link's time, in ms
    "unplaced": { segmentId: "s4", time: "14:02" },      // no usable time: no moment
  };
  const quotes = momentsFrom(snap, links).filter(m => m.kind === "quote");
  assert.deepEqual(quotes.map(m => [m.id, m.time - T]), [["p-quoted", 120], ["elsewhere", 250], ["p-quote", 300]]);
});

test("quote links: read from jv.quotes.links, and nothing when absent, broken or blocked", () => {
  assert.equal(QUOTE_LINKS_KEY, "jv.quotes.links");
  const store = value => ({ getItem: key => (key === QUOTE_LINKS_KEY ? value : null) });
  assert.deepEqual(readQuoteLinks(store(JSON.stringify({ n1: { segmentId: "s", time: 1 } }))), { n1: { segmentId: "s", time: 1 } });
  assert.deepEqual(readQuoteLinks(store(null)), {});
  assert.deepEqual(readQuoteLinks(store("{not json")), {});
  assert.deepEqual(readQuoteLinks(store("[1,2]")), {});
  assert.deepEqual(readQuoteLinks({ getItem() { throw new Error("blocked"); } }), {});
  assert.deepEqual(readQuoteLinks(undefined), {});
});

test("axis: from the first moment to now, never shorter than a minute, never ending before the last moment", () => {
  const moments = momentsFrom(SNAPSHOT);
  assert.deepEqual(axisFrom(moments, T + 900), { start: T + 10, end: T + 900 });
  assert.deepEqual(axisFrom(moments, T + 100), { start: T + 10, end: T + 500 }, "a clock behind the server still shows every mark");
  assert.deepEqual(axisFrom([{ time: T }], T + 5), { start: T + 5 - MIN_SPAN, end: T + 5 });
  assert.deepEqual(axisFrom([], T), { start: T - MIN_SPAN, end: T });
});

test("axis: time to a fraction and back, clamped to the ends", () => {
  const axis = { start: T, end: T + 400 };
  assert.equal(fractionOf(axis, T + 100), 0.25);
  assert.equal(fractionOf(axis, T - 50), 0);
  assert.equal(fractionOf(axis, T + 999), 1);
  assert.equal(timeAt(axis, 0.25), T + 100);
  assert.equal(timeAt(axis, -1), T);
  assert.equal(timeAt(axis, 2), T + 400);
  for (const t of [T, T + 1, T + 123.5, T + 400]) assert.equal(timeAt(axis, fractionOf(axis, t)), t);
  assert.equal(fractionOf({ start: T, end: T }, T), 0, "a zero span does not divide by zero");
});

test("after a moment: later items fade, later proposals go, and what was made at the moment stays", () => {
  const at = afterMoment(SNAPSHOT, T + 300);
  assert.deepEqual([...at.faded].sort(), ["n3", "pen"]);
  assert.deepEqual([...at.gone], ["p1"]);
  assert.ok(!at.faded.has("n2"), "accepted at exactly the moment: already there");
  const early = afterMoment(SNAPSHOT, T + 61);
  assert.deepEqual([...early.faded].sort(), ["cluster", "n-undone", "n2", "n3", "pen"]);
  assert.ok(!early.faded.has("no-time"), "a record without a time is never after anything");
  assert.ok(!early.faded.has("photo-2") && !early.gone.has("photo-2"), "sources are not drawn on the canvas");
  const now = afterMoment(SNAPSHOT, null);
  assert.equal(now.faded.size + now.gone.size, 0, "at now nothing is after");
});

test("labels: the words for each kind, with the time", () => {
  const [photo, accept, , accept2, command] = momentsFrom(SNAPSHOT);
  assert.equal(momentLabel(photo, clock), "Photograph · t+10");
  assert.equal(momentLabel(accept, clock), "Accepted · Onboarding loses people · t+60");
  assert.equal(momentLabel(accept2, clock), "Accepted · Too many fields before value · t+300");
  assert.equal(momentLabel(command, clock), "Command · summary · t+400");
  assert.equal(momentLabel({ kind: "quote", time: T + 9 }, clock), "Quote · t+9");
  const long = momentLabel({ kind: "accept", text: "A note whose words run on well past what a small label can carry", time: T }, clock);
  assert.ok(long.length < 50 && long.includes("…"), long);
  const whole = momentLabel({ kind: "accept", text: "A note whose words run on well past what a small label can carry", time: T }, clock, Infinity);
  assert.equal(whole, "Accepted · A note whose words run on well past what a small label can carry · t+0", "whole, for the slider's value text");
  assert.equal(momentLabel({ kind: "accept", text: "  ", time: T }, clock), "Accepted · t+0");
  const real = momentLabel(photo, s => new Date(s * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false }));
  assert.match(real, /^Photograph · \d\d:\d\d$/);
});

test("command words: from the transcript's feedback, falling back to the intent", () => {
  assert.equal(commandWords({ status: "recognised", intent: "planning" }), "agenda or schedule");
  assert.equal(commandWords({ status: "recognised", intent: "unheard-of" }), "unheard-of");
  assert.equal(commandWords(null), "command");
});

test("keys: arrows step between moments, Home goes to the first, End to now", () => {
  const moments = momentsFrom(SNAPSHOT);
  const last = moments.length - 1;
  assert.equal(step(moments, null, 1), null, "forward from now stays at now");
  assert.deepEqual(step(moments, null, -1), { time: moments[last].time, index: last }, "back from now is the newest moment");
  assert.deepEqual(step(moments, { time: moments[2].time, index: 2 }, -1), { time: moments[1].time, index: 1 });
  assert.deepEqual(step(moments, { time: moments[2].time, index: 2 }, 1), { time: moments[3].time, index: 3 });
  assert.equal(step(moments, { time: moments[last].time, index: last }, 1), null, "past the newest is now");
  assert.deepEqual(step(moments, { time: moments[0].time, index: 0 }, -1), { time: moments[0].time, index: 0 }, "the first stays first");
  assert.deepEqual(step(moments, null, "first"), { time: moments[0].time, index: 0 });
  assert.equal(step(moments, { time: T + 100, index: 1 }, "now"), null);
  // A pointer left between moments: the keys go to the neighbours of that time.
  assert.deepEqual(step(moments, { time: T + 250, index: null }, 1), { time: T + 300, index: 3 });
  assert.deepEqual(step(moments, { time: T + 250, index: null }, -1), { time: T + 200, index: 2 });
  assert.deepEqual(step(moments, { time: T + 1, index: null }, -1), { time: T + 10, index: 0 });
  assert.equal(step(moments, { time: T + 999, index: null }, 1), null);
  assert.equal(step([], null, -1), null, "no moments: always now");
  // Two moments in the same second are both reachable.
  const same = [{ key: "a", time: T }, { key: "b", time: T }];
  assert.deepEqual(step(same, { time: T, index: 0 }, 1), { time: T, index: 1 });
});
