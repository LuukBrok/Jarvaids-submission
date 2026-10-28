/**
 * Quote notes' pure parts, without a browser (DESIGN.md 1.2).
 *
 * The marker text from a timestamp, the link store with a fake storage and
 * its in-memory fallback, resolving an accepted item through the proposal
 * it came from, the link a note's own text implies on another device, and
 * the People colour with its wrap after ten.
 *
 *     node --test tests/quote-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { quoteTime, quoteText, quoteWords, splitMarker, personIndex, personTone, createLinkStore,
  parseLinks, flagOn, storedLink, textLink, speakerLabel, LINKS_KEY, FLAG_KEY, MAX_LINKS } from "../tools/quote.mjs";

/** Seconds since the epoch for a wall-clock time in this machine's zone, so
 * the tests hold in any time zone. */
const at = (h, m, s = 0) => new Date(2026, 9, 19, h, m, s).getTime() / 1000;

/** A Storage stand-in: a Map behind getItem and setItem, with switches to
 * make either throw the way a blocked or full localStorage does. */
function fakeStorage(initial = {}) {
  const items = new Map(Object.entries(initial));
  return {
    items, failRead: false, failWrite: false,
    getItem(key) { if (this.failRead) throw new Error("SecurityError"); return items.has(key) ? items.get(key) : null; },
    setItem(key, value) { if (this.failWrite) throw new Error("QuotaExceededError"); items.set(key, String(value)); },
  };
}

const link = (segmentId, extra = {}) => ({ segmentId, time: at(14, 2), speakerActorId: "a2", ...extra });

// ------------------------------------------------------------------ marker

test("the marker is the time it was said, HH:MM on a 24 hour clock", () => {
  assert.equal(quoteTime(at(14, 2, 59)), "14:02");
  assert.equal(quoteTime(at(9, 5)), "09:05");
  assert.equal(quoteTime(at(0, 0)), "00:00");
  assert.equal(quoteTime(at(23, 59)), "23:59");
  // The server's created_at is seconds; milliseconds are read as such too.
  assert.equal(quoteTime(at(14, 2) * 1000), "14:02");
  for (const bad of [null, undefined, "", "soon", NaN, 0, -5]) assert.equal(quoteTime(bad), null, String(bad));
});

test("the note text is the words, a middle dot and the time", () => {
  assert.equal(quoteText("We lose people at step three", at(14, 2)), "We lose people at step three · 14:02");
  assert.equal(quoteText("  spread\n over   lines ", at(9, 30)), "spread over lines · 09:30");
  assert.equal(quoteText("No time known", null), "No time known");
  assert.equal(quoteWords(" a \t b "), "a b");
});

test("the trailing marker is found, and only at the end", () => {
  assert.deepEqual(splitMarker("Step three · 14:02"), { words: "Step three", marker: " · 14:02", time: "14:02" });
  assert.equal(splitMarker("Meet at 14:02 · then lunch"), null);
  assert.equal(splitMarker("Step three 14:02"), null);
  assert.equal(splitMarker("Step three · 4:02"), null);
  assert.equal(splitMarker(undefined), null);
  // Joined back, the parts are the text exactly: the note's textContent is unchanged.
  const parts = splitMarker("a · b · 10:15");
  assert.equal(parts.words + parts.marker, "a · b · 10:15");
});

// ------------------------------------------------------------------ people

test("the People colour is the speaker's place among the members, wrapping after ten", () => {
  const members = Array.from({ length: 12 }, (_, i) => ({ id: `a${i + 1}` }));
  assert.equal(personIndex(members, "a1"), 1);
  assert.equal(personIndex(members, "a5"), 5);
  assert.equal(personIndex(members, "a10"), 10);
  assert.equal(personIndex(members, "a11"), 1);
  assert.equal(personIndex(members, "a12"), 2);
  // Someone not in the session claims no colour at all.
  assert.equal(personIndex(members, "stranger"), 0);
  assert.equal(personIndex(undefined, "a1"), 0);
});

test("the first five People colours carry ink, the deep five carry paper", () => {
  assert.deepEqual([1, 2, 3, 4, 5].map(personTone), ["full", "full", "full", "full", "full"]);
  assert.deepEqual([6, 7, 8, 9, 10].map(personTone), ["deep", "deep", "deep", "deep", "deep"]);
});

// -------------------------------------------------------------- link store

test("a link is written to storage under jv.quotes.links as one JSON object", () => {
  const storage = fakeStorage();
  const store = createLinkStore(storage);
  assert.equal(store.persistent, true);
  assert.equal(store.set("p1", link("s1")), true);
  assert.deepEqual(JSON.parse(storage.items.get(LINKS_KEY)), { p1: { segmentId: "s1", time: at(14, 2), speakerActorId: "a2" } });
  // A second page load reads it back.
  assert.deepEqual(createLinkStore(storage).get("p1"), link("s1"));
});

test("writing merges what another tab stored, so neither tab drops the other's links", () => {
  const storage = fakeStorage();
  const one = createLinkStore(storage), two = createLinkStore(storage);
  one.set("p1", link("s1"));
  two.set("p2", link("s2"));
  assert.deepEqual(Object.keys(JSON.parse(storage.items.get(LINKS_KEY))).sort(), ["p1", "p2"]);
});

test("a damaged entry costs only itself", () => {
  const stored = JSON.stringify({ good: link("s1"), noSegment: { time: 1 }, notObject: 7 });
  const store = createLinkStore(fakeStorage({ [LINKS_KEY]: stored }));
  assert.deepEqual(store.get("good"), link("s1"));
  assert.equal(store.get("noSegment"), null);
  assert.equal(store.get("notObject"), null);
  assert.deepEqual(parseLinks("not json"), {});
  assert.deepEqual(parseLinks("[1,2]"), {});
});

test("a storage that throws on reading: links are kept in memory, and the person is told once", () => {
  const storage = fakeStorage();
  storage.failRead = true;
  let told = 0;
  const store = createLinkStore(storage, { onFallback: () => told++ });
  assert.equal(store.persistent, false);
  assert.equal(told, 1);
  store.set("p1", link("s1"));
  store.set("p2", link("s2"));
  assert.deepEqual(store.get("p1"), link("s1"));
  assert.equal(storage.items.has(LINKS_KEY), false);
  assert.equal(told, 1);
});

test("a storage that throws on writing: the link still holds in memory, told once", () => {
  const storage = fakeStorage();
  storage.failWrite = true;
  let told = 0;
  const store = createLinkStore(storage, { onFallback: () => told++ });
  assert.equal(store.persistent, true);
  store.set("p1", link("s1"));
  store.set("p2", link("s2"));
  assert.equal(told, 1);
  assert.equal(store.persistent, false);
  assert.deepEqual(store.get("p1"), link("s1"));
  assert.deepEqual(store.get("p2"), link("s2"));
});

test("no storage at all is the same in-memory fallback", () => {
  let told = 0;
  const store = createLinkStore(null, { onFallback: () => told++ });
  store.set("p1", link("s1"));
  assert.deepEqual(store.get("p1"), link("s1"));
  assert.equal(told, 1);
});

test("the store keeps the newest links only", () => {
  const storage = fakeStorage();
  const store = createLinkStore(storage);
  for (let i = 0; i <= MAX_LINKS; i++) store.set(`p${i}`, link(`s${i}`));
  assert.equal(store.size, MAX_LINKS);
  assert.equal(store.get("p0"), null);
  assert.deepEqual(store.get(`p${MAX_LINKS}`), link(`s${MAX_LINKS}`));
  // Measured, against the guess in quote.mjs: the full store is well under 100 KB.
  assert.ok(storage.items.get(LINKS_KEY).length < 100_000, `${storage.items.get(LINKS_KEY).length} characters`);
});

test("the flag is on unless it says off, and on when storage cannot be read", () => {
  assert.equal(flagOn(fakeStorage()), true);
  for (const off of ["0", "false", "off", " OFF "]) assert.equal(flagOn(fakeStorage({ [FLAG_KEY]: off })), false, off);
  assert.equal(flagOn(fakeStorage({ [FLAG_KEY]: "1" })), true);
  const blocked = fakeStorage(); blocked.failRead = true;
  assert.equal(flagOn(blocked), true);
  assert.equal(flagOn(null), true);
});

// --------------------------------------------------------------- resolving

const proposal = (id, text) => ({ id, kind: "proposal", data: { proposal_kind: "content", status: "needs_review", text } });
const item = (id, proposalId, text) => ({ id, kind: "item", data: { item_kind: "content", status: "accepted", proposal_id: proposalId, text } });
const segment = (id, text, createdAt, extra = {}) => ({ id, kind: "transcript_segment",
  data: { status: "final", text, created_at: createdAt, speaker_actor_id: "a2", attribution: "per_connection", provenance: { synthetic: true }, ...extra } });

test("an accepted item is linked through the proposal it came from", () => {
  const store = createLinkStore(fakeStorage());
  store.set("p1", link("s1"));
  assert.deepEqual(storedLink(store, proposal("p1", "x")), link("s1"));
  assert.deepEqual(storedLink(store, item("i1", "p1", "x")), link("s1"));
  assert.equal(storedLink(store, item("i2", "p9", "x")), null);
  assert.equal(storedLink(store, item("i3", undefined, "x")), null);
  // Only an item points through proposal_id: a proposal's own id decides for it.
  assert.equal(storedLink(store, { id: "p2", kind: "proposal", data: { proposal_id: "p1" } }), null);
  assert.equal(storedLink(store, null), null);
});

test("on another device, a note's own text finds its line: same words, same minute", () => {
  const snapshot = { members: [{ id: "a1", name: "Sanne" }, { id: "a2", name: "Jo" }], records: [
    segment("s1", "People skip the tour", at(14, 2, 10)),
    segment("s2", "Too many fields", at(14, 3)),
  ] };
  const note = item("i1", "p1", "People skip the tour · 14:02");
  assert.deepEqual(textLink(snapshot, note), { segmentId: "s1", time: at(14, 2, 10), speakerActorId: "a2" });
  // A different minute, different words or no marker: no link, never a guess.
  assert.equal(textLink(snapshot, item("i2", "p2", "People skip the tour · 14:05")), null);
  assert.equal(textLink(snapshot, item("i3", "p3", "People skip the tours · 14:02")), null);
  assert.equal(textLink(snapshot, item("i4", "p4", "People skip the tour")), null);
});

test("two lines with the same words in the same minute are ambiguous, so neither is claimed", () => {
  const snapshot = { members: [], records: [segment("s1", "Yes", at(14, 2, 1)), segment("s2", "Yes", at(14, 2, 40))] };
  assert.equal(textLink(snapshot, proposal("p1", "Yes · 14:02")), null);
});

test("the speaker is named as the transcript names them", () => {
  const snapshot = { members: [{ id: "a1", name: "Sanne" }, { id: "a2", name: "Jo" }], records: [
    segment("s1", "a", at(14, 2)),
    segment("s2", "b", at(14, 2), { attribution: "voice_identified", speaker_name: "Pieter" }),
    segment("s3", "c", at(14, 2), { attribution: "unidentified" }),
  ] };
  assert.equal(speakerLabel(snapshot, link("s1")), "Jo");
  assert.equal(speakerLabel(snapshot, link("s2")), "Pieter");
  assert.equal(speakerLabel(snapshot, link("s3")), "Unknown speaker");
  // A line no longer in the snapshot is named by the device that sent it.
  assert.equal(speakerLabel(snapshot, link("gone", { speakerActorId: "a1" })), "Sanne");
});
