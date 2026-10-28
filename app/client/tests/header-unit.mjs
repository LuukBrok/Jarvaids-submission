/**
 * The header's pure parts: the state chip for every session and listening
 * state, the keep-alive countdown and its estimate of the lease, and the
 * participant line; the Jarvaids menu's commands and when they can be
 * started, and the collecting chip's words.
 *
 *     node --test tests/header-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chipState, chipClass, formatCountdown, keepAliveWords, createLease, participantLine, personTone,
  LEASE_MS, HEARTBEAT_MS, URGENT_MS, COMMAND_GROUPS, LIFECYCLE_WORDS, RECOGNISED_ONLY, commandText,
  commandAvailability, commandSentWords, collectingPill } from "../header.mjs";

test("the chip says the session's state, in app.mjs's words", () => {
  const cases = [
    ["draft", false, "Not started", "chip-idle"],
    ["active", false, "Session open", "chip-open"],
    ["paused", false, "Paused", "chip-paused"],
    ["closed", false, "Ended", "chip-ended"],
  ];
  for (const [state, listening, word, className] of cases) {
    const chip = chipState(state, listening);
    assert.equal(chip.word, word, state);
    assert.equal(chip.className, className, state);
    assert.equal(chip.timer, false, `${state} shows no timer`);
    assert.equal(chip.bars, false, `${state} shows no bars`);
    assert.equal(chipClass(chip), `chip state-chip ${className}`);
  }
});

test("Listening, with the bars and the timer, only while the session is open", () => {
  const on = chipState("active", true);
  assert.deepEqual([on.key, on.word, on.className, on.timer, on.bars], ["listening", "Listening", "chip-listening", true, true]);
  // A microphone still on as the session pauses or ends is not listening to
  // the session: the chip says the session's state.
  assert.equal(chipState("paused", true).word, "Paused");
  assert.equal(chipState("closed", true).word, "Ended");
  assert.equal(chipState("draft", true).word, "Not started");
  assert.equal(chipState("paused", true).bars, false);
});

test("an unknown state is shown as it is, never as open", () => {
  assert.equal(chipState("deleted").word, "deleted");
  assert.equal(chipState("deleted").className, "chip-idle");
  assert.equal(chipState(undefined).word, "Offline");
  assert.equal(chipState("listening").word, "listening", "a state named listening is not this device listening");
});

test("the countdown is M:SS, rounded up, never negative", () => {
  assert.equal(formatCountdown(LEASE_MS), "5:00");
  assert.equal(formatCountdown(LEASE_MS - 1), "5:00", "4:59.999 still has five minutes on the clock");
  assert.equal(formatCountdown(LEASE_MS - 1000), "4:59");
  assert.equal(formatCountdown(61_000), "1:01");
  assert.equal(formatCountdown(60_000), "1:00");
  assert.equal(formatCountdown(9_000), "0:09");
  assert.equal(formatCountdown(1), "0:01");
  assert.equal(formatCountdown(0), "0:00");
  assert.equal(formatCountdown(-5000), "0:00");
  assert.equal(formatCountdown(NaN), "0:00");
});

test("the keep-alive words: unknown, counting, urgent, due", () => {
  const unknown = keepAliveWords(null);
  assert.equal(unknown.countdown, null);
  assert.match(unknown.before, /within 5 minutes unless a facilitator keeps it running\.$/);
  assert.equal(unknown.urgent, false);
  const counting = keepAliveWords(4 * 60_000 + 12_000);
  assert.equal(counting.before + counting.countdown + counting.after,
    "Capture pauses itself in 4:12 unless a facilitator keeps it running.");
  assert.equal(counting.urgent, false);
  assert.equal(keepAliveWords(URGENT_MS).urgent, false, "a full minute is not yet urgent");
  assert.equal(keepAliveWords(URGENT_MS - 1).urgent, true, "under a minute is");
  const due = keepAliveWords(0);
  assert.equal(due.countdown, null);
  assert.match(due.before, /^Capture is due to pause now/);
  assert.equal(due.urgent, true);
});

test("the lease is unknown for a session already open at the first look", () => {
  const lease = createLease();
  lease.observe({ now: 1000, state: "active", heartbeat: false });
  assert.equal(lease.remaining(1000), null);
});

test("an activation seen happening starts the five minutes", () => {
  const lease = createLease();
  lease.observe({ now: 0, state: "draft", heartbeat: false });
  lease.observe({ now: 10_000, state: "active", heartbeat: false });
  assert.equal(lease.remaining(10_000), LEASE_MS);
  assert.equal(lease.remaining(10_000 + 4 * 60_000), 60_000);
  assert.equal(lease.remaining(10_000 + LEASE_MS + 1), 0, "never below zero");
});

test("heartbeats renew from the last whole beat, so the estimate errs early", () => {
  const lease = createLease();
  lease.observe({ now: 0, state: "paused", heartbeat: false });
  lease.observe({ now: 1_000, state: "active", heartbeat: true });   // resumed, heartbeat on with it
  // 95 seconds of heartbeat seen: beats landed at 31 s, 61 s and 91 s.
  lease.observe({ now: 96_000, state: "active", heartbeat: true });
  lease.observe({ now: 97_000, state: "active", heartbeat: false });  // the tab was hidden
  assert.equal(lease.remaining(97_000), 91_000 + LEASE_MS - 97_000);
  // A heartbeat on for less than one beat renews nothing beyond the activation.
  const short = createLease();
  short.observe({ now: 0, state: "draft", heartbeat: false });
  short.observe({ now: 5_000, state: "active", heartbeat: true });
  short.observe({ now: 5_000 + HEARTBEAT_MS - 1, state: "active", heartbeat: false });
  assert.equal(short.remaining(5_000), LEASE_MS);
});

test("a heartbeat switched on later starts counting beats again from then", () => {
  const lease = createLease();
  lease.observe({ now: 0, state: "active", heartbeat: false });       // unknown
  lease.observe({ now: 10_000, state: "active", heartbeat: true });   // Keep capture running
  assert.equal(lease.remaining(10_000), null, "no beat has landed yet");
  lease.observe({ now: 41_000, state: "active", heartbeat: true });
  assert.equal(lease.remaining(41_000), 40_000 + LEASE_MS - 41_000);
});

test("leaving the open state forgets the lease", () => {
  const lease = createLease();
  lease.observe({ now: 0, state: "draft" });
  lease.observe({ now: 1, state: "active", heartbeat: false });
  lease.observe({ now: 2, state: "paused", heartbeat: false });
  assert.equal(lease.remaining(2), null);
});

const member = (id, name, consent = 1) => ({ id, name, role: "participant", consent_version: consent });
const session = (...members) => ({ session: { policy_version: 1 }, members });

test("the participant line: everyone agreed, or who capture waits for", () => {
  const all = participantLine(session(member("a", "Pieter"), member("b", "Sam")));
  assert.equal(all.text, "everyone agreed");
  assert.equal(all.spoken, "2 people: Pieter and Sam. ");
  const one = participantLine(session(member("a", "Pieter"), member("b", "Sam", 0)));
  assert.equal(one.text, "waiting for Sam");
  const two = participantLine(session(member("a", "Pieter"), member("b", "Sam", 0), member("c", "Jo", null)));
  assert.equal(two.text, "waiting for Sam and Jo");
  const three = participantLine(session(member("a", "Pieter", 0), member("b", "Sam", 0), member("c", "Jo", 0)));
  assert.equal(three.text, "waiting for Pieter, Sam and Jo");
  assert.equal(participantLine(session(member("a", "Pieter"))).spoken, "1 person: Pieter. ");
});

test("people are circles in join order, coloured from --person-N", () => {
  const line = participantLine(session(member("a", "pieter"), member("b", "Sam"), member("c", " jo"), member("d", "")));
  assert.deepEqual(line.people.map(p => p.initial), ["P", "S", "J", "?"]);
  assert.deepEqual(line.people.map(p => p.fill), ["var(--person-1)", "var(--person-2)", "var(--person-3)", "var(--person-4)"]);
  assert.deepEqual(line.people.map(p => p.agreed), [true, true, true, true]);
  // Ink on the five accents, paper on their -deep steps; the eleventh wraps.
  assert.equal(personTone(4).text, "var(--text)");
  assert.equal(personTone(5).fill, "var(--person-6)");
  assert.equal(personTone(5).text, "var(--text-on-deep)");
  assert.equal(personTone(10).fill, "var(--person-1)");
});

// ------------------------------------------------- the Jarvaids menu

/** The phrases under each `## heading` of docs/COMMAND-PHRASES.md. */
function phraseBook() {
  const text = readFileSync(new URL("../../../docs/COMMAND-PHRASES.md", import.meta.url), "utf8");
  const book = new Map();
  let heading = null;
  for (const line of text.split(/\r?\n/)) {
    const h = line.match(/^## (.+)$/);
    if (h) { heading = h[1].trim(); book.set(heading, []); continue; }
    const item = line.match(/^\d+\. (.+)$/);
    if (heading && item) book.get(heading).push(item[1].trim());
  }
  return book;
}

test("the sheet's eight groups use three phrases each, verbatim from COMMAND-PHRASES.md", () => {
  const book = phraseBook();
  assert.deepEqual(COMMAND_GROUPS.map(g => g.key),
    ["voting", "todo", "requirements", "planning", "summary", "visualisation", "comparison", "suggestions"]);
  for (const g of COMMAND_GROUPS) {
    assert.equal(g.examples.length, 3, g.key);
    assert.equal(new Set(g.examples).size, 3, `${g.key} has three different examples`);
    for (const phrase of g.examples) assert.ok(book.get(g.key)?.includes(phrase), `"${phrase}" is listed under ## ${g.key}`);
    if (g.executed) assert.ok(book.get(g.key).includes(g.start), `the menu's "${g.start}" is listed under ## ${g.key}`);
  }
});

test("voting, lists, calendar and summary are offered as carried out", () => {
  assert.deepEqual(COMMAND_GROUPS.filter(g => g.executed).map(g => g.label), ["Poll", "To-do list", "Requirements and wishes", "Calendar", "Summary"]);
  assert.deepEqual(COMMAND_GROUPS.filter(g => !g.executed).map(g => g.label), ["Visualisation", "Comparison", "Suggestions"]);
  assert.equal(RECOGNISED_ONLY, "Recognised, not yet carried out");
  for (const g of COMMAND_GROUPS.filter(g => !g.executed)) assert.equal(commandText(g.key), null, `${g.key} sends nothing`);
});

test("a menu item sends the addressed words a person would say", () => {
  assert.equal(commandText("voting"), "Hey Jarvaids, create a poll.");
  assert.equal(commandText("todo"), "Hey Jarvaids, make a to do list.");
  assert.equal(commandText("requirements"), "Hey Jarvaids, make a requirements list.");
  assert.equal(commandText("planning"), "Hey Jarvaids, create a calendar.");
  assert.equal(commandText("nonsense"), null);
  for (const key of ["voting", "todo", "requirements", "planning"]) assert.match(commandSentWords(key), /^Asked for a /);
});

test("the lifecycle paragraph names close, accept, reopen and cancel, and says a poll cannot be reopened", () => {
  for (const word of ["close the to do list", "accept the to do list", "reopen the to do list", "cancel the to do list",
    "close the poll", "accept the results", "cancel the poll"]) assert.ok(LIFECYCLE_WORDS.includes(word), word);
  assert.match(LIFECYCLE_WORDS, /a poll cannot be reopened/);
  assert.doesNotMatch(LIFECYCLE_WORDS, /\u2014/, "no em dash");
});

const workspace = (patch = {}) => ({
  actor_id: "a",
  members: [{ id: "a", name: "Pieter", role: patch.role ?? "facilitator" }],
  session: { state: patch.state ?? "active", automatic_workspace: patch.automatic ?? true },
  records: patch.records ?? [],
});

test("commands can be started only by an editor, while capture runs, in the automatic workspace", () => {
  assert.deepEqual(commandAvailability(workspace()), { enabled: true, reason: "" });
  assert.equal(commandAvailability(workspace({ role: "participant" })).enabled, true);
  const cases = [
    [workspace({ role: "viewer" }), /read-only/],
    [workspace({ state: "paused" }), /while capture runs/],
    [workspace({ state: "draft" }), /while capture runs/],
    [workspace({ state: "closed" }), /has ended/],
    [workspace({ automatic: false }), /review mode, start a command by saying it/],
    [null, /Not connected/],
  ];
  for (const [s, reason] of cases) {
    const can = commandAvailability(s);
    assert.equal(can.enabled, false);
    assert.match(can.reason, reason);
  }
});

// ------------------------------------------------- the collecting chip

const doc = (id, type, state, at) => ({ id, kind: "command_document", data: { document_type: type, state, created_at: at } });
const poll = (id, state, at) => ({ id, kind: "poll", data: { state, created_at: at } });

test("the collecting chip names what collects, and only while capture runs", () => {
  assert.equal(collectingPill(workspace()), null, "nothing collecting, no chip");
  let pill = collectingPill(workspace({ records: [doc("d1", "todo", "collecting", 1)] }));
  assert.equal(pill.words, "Collecting: to-do");
  assert.deepEqual(pill.targets, ["d1"]);
  assert.equal(pill.label, "Collecting: to-do. Show it on the canvas");
  pill = collectingPill(workspace({ records: [doc("d2", "calendar", "collecting", 2), doc("d1", "todo", "collecting", 1)] }));
  assert.equal(pill.words, "Collecting: to-do, calendar", "in the order they were started");
  assert.deepEqual(pill.targets, ["d2", "d1"], "newest first");
  assert.match(pill.label, /Show the next one on the canvas$/);
  assert.equal(collectingPill(workspace({ records: [poll("p1", "open", 1)] })).words, "Poll open");
  pill = collectingPill(workspace({ records: [poll("p1", "open", 3), doc("d1", "requirements", "collecting", 1)] }));
  assert.equal(pill.words, "Poll open \u00b7 Collecting: requirements");
  assert.deepEqual(pill.targets, ["p1", "d1"]);
});

test("closed, accepted, cancelled and draft records do not collect", () => {
  const records = [doc("a", "todo", "reviewing", 1), doc("b", "calendar", "accepted", 2), doc("c", "requirements", "cancelled", 3),
    poll("p", "draft", 4), poll("q", "closing", 5), poll("r", "closed", 6), doc("d", "unknown", "collecting", 7)];
  assert.equal(collectingPill(workspace({ records })), null);
  const collecting = [doc("e", "todo", "collecting", 1), doc("f", "todo", "collecting", 2)];
  assert.equal(collectingPill(workspace({ records: collecting })).words, "Collecting: to-do", "one word per kind");
  for (const state of ["paused", "closed", "draft"])
    assert.equal(collectingPill(workspace({ state, records: collecting })), null, `no chip while ${state}`);
});
