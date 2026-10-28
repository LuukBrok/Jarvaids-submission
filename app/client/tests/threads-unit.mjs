/**
 * Provenance threads' pure parts, without a browser (DESIGN.md 1.2).
 *
 * Where a thread leaves a rectangle, the curve it draws, which origins a note
 * has from a snapshot and the quote links, the selectors those origins are
 * looked up by, and the coalescer that keeps recomputes to one per frame.
 * The page half (what is on screen) is in threads-browser.mjs.
 *
 *     node --test tests/threads-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { centre, createCoalescer, edgeToward, LINKS_KEY, originSelectors, readLinks, resolveOrigins,
  threadEnds, threadPath } from "../tools/threads.mjs";

// ------------------------------------------------------------------ geometry

const rect = { x: 0, y: 0, w: 100, h: 50 };

test("a point beside a rectangle is reached from the side facing it, level with it", () => {
  assert.deepEqual(edgeToward(rect, { x: 300, y: 25 }), { x: 100, y: 25, nx: 1, ny: 0 });
  assert.deepEqual(edgeToward(rect, { x: -300, y: 30 }), { x: 0, y: 30, nx: -1, ny: 0 });
  assert.deepEqual(edgeToward(rect, { x: 40, y: -200 }), { x: 40, y: 0, nx: 0, ny: -1 });
  assert.deepEqual(edgeToward(rect, { x: 60, y: 400 }), { x: 60, y: 50, nx: 0, ny: 1 });
});

test("the side is the one a ray from the centre leaves through, not the nearest coordinate", () => {
  // Far below and to the right: the ray leaves through the bottom (250/50 < 375/25).
  const p = edgeToward(rect, { x: 300, y: 400 });
  assert.equal(p.y, 50);
  assert.deepEqual([p.nx, p.ny], [0, 1]);
});

test("a thread never leaves from a corner: it slides along the side, kept 8px in", () => {
  assert.deepEqual(edgeToward(rect, { x: 300, y: -40 }), { x: 100, y: 8, nx: 1, ny: 0 });
  assert.deepEqual(edgeToward(rect, { x: 300, y: 90 }), { x: 100, y: 42, nx: 1, ny: 0 });
  // A side shorter than two insets gives its middle.
  assert.deepEqual(edgeToward({ x: 0, y: 0, w: 100, h: 10 }, { x: 300, y: 7 }), { x: 100, y: 5, nx: 1, ny: 0 });
});

test("a point inside (a note within its group's outline) is reached from the nearest side, pointing in", () => {
  const hull = { x: 0, y: 0, w: 400, h: 300 };
  assert.deepEqual(edgeToward(hull, { x: 200, y: 20 }), { x: 200, y: 0, nx: 0, ny: 1 });
  assert.deepEqual(edgeToward(hull, { x: 390, y: 150 }), { x: 400, y: 150, nx: -1, ny: 0 });
});

test("a zero-sized origin is its own point", () => {
  const p = edgeToward({ x: 5, y: 5, w: 0, h: 0 }, { x: 50, y: 5 });
  assert.deepEqual([p.x, p.y], [5, 5]);
});

test("the ends: the origin's edge facing the note, then the note's edge facing that", () => {
  const note = { x: 100, y: 100, w: 200, h: 120 };      // centre 200, 160
  const crop = { x: 900, y: 140, w: 160, h: 80 };        // to the right, overlapping in height
  const { note: a, origin: b } = threadEnds(note, crop);
  assert.deepEqual(b, { x: 900, y: 160, nx: -1, ny: 0 }, "the crop's left edge, level with the note's centre");
  assert.deepEqual(a, { x: 300, y: 160, nx: 1, ny: 0 }, "the note's right edge, level with that");
  assert.deepEqual(centre(note), { x: 200, y: 160 });
});

test("a group outline around the note is met at its nearest side", () => {
  const note = { x: 112, y: 112, w: 200, h: 100 };
  const hull = { x: 100, y: 100, w: 500, h: 300 };
  const { note: a, origin: b } = threadEnds(note, hull);
  assert.deepEqual([b.y, b.ny], [100, 1], "the hull's top, pointing in");
  assert.deepEqual([a.y, a.ny], [112, -1], "the note's top, pointing out");
});

test("the thread is one cubic curve that leaves and enters along each end's normal", () => {
  const d = threadPath({ x: 0, y: 0, nx: 1, ny: 0 }, { x: 100, y: 0, nx: -1, ny: 0 });
  assert.equal(d, "M 0 0 C 40 0 60 0 100 0", "pulled 40% of the distance");
  assert.match(d, /^M [-\d.]+ [-\d.]+ C( [-\d.]+ [-\d.]+){3}$/, "one move, one cubic, nothing else");
});

test("a long thread's pull is capped, and coordinates keep two decimals", () => {
  const d = threadPath({ x: 0.123, y: 0, nx: 1, ny: 0 }, { x: 1000, y: 0.456, nx: -1, ny: 0 });
  assert.equal(d, "M 0.12 0 C 160.12 0 840 0.46 1000 0.46");
});

// ------------------------------------------------------------------- origins

const accepted = (id, extra = {}) => ({ id, kind: "item", revision: 1,
  data: { item_kind: "content", status: "accepted", origin: "human", text: id, accepted_by: "a1", refs: [], ...extra } });
const proposed = (id, extra = {}) => ({ id, kind: "proposal", revision: 1,
  data: { proposal_kind: "content", status: "needs_review", origin: "fixture", text: id, refs: [], ...extra } });
const cluster = (id, members, kind = "item", status = "accepted") => ({ id, kind, revision: 1,
  data: { item_kind: "relationship", proposal_kind: "relationship", form: "cluster", status, text: "G",
    refs: members.map(m => ({ id: m, revision: 1 })) } });
const arrow = (id, from, to) => ({ id, kind: "item", revision: 1,
  data: { item_kind: "arrow", status: "accepted", origin: "human", from: { id: from }, to: { id: to } } });
const section = (id, member_ids) => ({ id, kind: "item", revision: 1,
  data: { item_kind: "section", status: "accepted", title: "Risks", form: "free", member_ids } });

const SNAP = {
  members: [{ id: "a1", name: "Sanne" }],
  records: [
    accepted("i1", { proposal_id: "p0", region_id: "r1", refs: [{ id: "src", revision: 1 }] }),
    accepted("i2"),
    accepted("bare", { accepted_by: undefined }),
    proposed("p1", { region_id: "r2", refs: [{ id: "src", revision: 1 }] }),
    proposed("typed", { origin: "human", author_id: "a1" }),
    cluster("g1", ["i1", "i2"]),
    cluster("g-proposed", ["p0"], "proposal", "needs_review"),   // made before acceptance, names the proposal
    cluster("g-decided", ["i1"], "proposal", "accepted"),        // a decided proposal: its item is the group
    cluster("g-rejected", ["i1"], "proposal", "rejected"),  // decided: not on the canvas
    section("s1", ["i2", "p1"]),
    arrow("a-1", "i1", "i2"),
    arrow("a-2", "p0", "p1"),                               // drawn to the proposal before it was accepted
    { id: "a-proposed", kind: "proposal", revision: 1,
      data: { proposal_kind: "canvas", canvas_kind: "arrow", status: "needs_review", origin: "model",
        canvas_data: { from: { id: "p1" }, to: { x: 0, y: 0 } } } },
    { id: "a-rejected", kind: "proposal", revision: 1,
      data: { proposal_kind: "canvas", canvas_kind: "arrow", status: "rejected", origin: "model",
        canvas_data: { from: { id: "p1" }, to: { id: "i2" } } } },
    { id: "src", kind: "source", revision: 1, data: { source_type: "image" } },
  ],
};

test("an accepted note: its crop, its quote, who accepted it, its groups and its connectors", () => {
  const links = { p0: { segmentId: "seg-a", time: 842, speakerActorId: "a1" } };
  assert.deepEqual(resolveOrigins("i1", SNAP, links), [
    { kind: "crop", ids: ["i1", "p0"] },
    { kind: "transcript", segmentId: "seg-a" },
    { kind: "person", actorId: "a1" },
    { kind: "group", id: "g1" },
    { kind: "group", id: "g-proposed" },
    { kind: "connector", id: "a-1" },
    { kind: "connector", id: "a-2" },
  ]);
});

test("a proposed note: its crop, the section it is in, and connectors, proposed ones included; nobody accepted it", () => {
  assert.deepEqual(resolveOrigins("p1", SNAP, {}), [
    { kind: "crop", ids: ["p1"] },
    { kind: "group", id: "s1" },
    { kind: "connector", id: "a-2" },
    { kind: "connector", id: "a-proposed" },
  ]);
});

test("a quote link is found under the note's own id too", () => {
  const origins = resolveOrigins("typed", SNAP, { typed: { segmentId: "s9", time: 1 } });
  assert.deepEqual(origins, [{ kind: "transcript", segmentId: "s9" }]);
});

test("a note with no origins has none, and so draws no threads", () => {
  assert.deepEqual(resolveOrigins("bare", SNAP, {}), []);
  assert.deepEqual(resolveOrigins("typed", SNAP, {}), []);
});

test("only notes have origins: a group, an arrow, a source or a missing id has none", () => {
  for (const id of ["g1", "a-1", "src", "nowhere"]) assert.deepEqual(resolveOrigins(id, SNAP, {}), [], id);
  assert.deepEqual(resolveOrigins("i1", null, {}), []);
});

test("a broken quote link is ignored rather than drawn", () => {
  const origins = resolveOrigins("i1", SNAP, { i1: { segmentId: "" }, p0: "nonsense" });
  assert.equal(origins.some(o => o.kind === "transcript"), false);
});

test("the quote links are read from storage, and anything that is not an object reads as none", () => {
  const store = value => ({ getItem: key => (key === LINKS_KEY ? value : null) });
  assert.deepEqual(readLinks(store('{"n1":{"segmentId":"s1","time":3}}')), { n1: { segmentId: "s1", time: 3 } });
  for (const bad of [null, "", "not json", "[1,2]", "7", "null"]) assert.deepEqual(readLinks(store(bad)), {}, String(bad));
  assert.deepEqual(readLinks({ getItem() { throw new Error("blocked"); } }), {});
  assert.deepEqual(readLinks(undefined), {});
});

test("each origin is looked up by the markup contracts, rail first for a crop", () => {
  assert.deepEqual(originSelectors({ kind: "crop", ids: ["i1", "p0"] }, "i1"), [
    { scope: "page", selector: '.proposal[data-id="i1"] img' },
    { scope: "page", selector: '.proposal[data-id="p0"] img' },
    { scope: "board", selector: '.note[data-id="i1"] .crop img' },
  ]);
  assert.deepEqual(originSelectors({ kind: "transcript", segmentId: "s1" }), [
    { scope: "page", selector: '[id="seg-s1"]' },
    { scope: "page", selector: '.transcript-row[data-segment-id="s1"]' },
  ]);
  assert.deepEqual(originSelectors({ kind: "person", actorId: "a1" }), [{ scope: "page", selector: '.person[data-actor-id="a1"]' }]);
  assert.deepEqual(originSelectors({ kind: "group", id: "g1" }).map(s => s.selector), ['.hull[data-id="g1"]', '[data-id="g1"]:not(.note)']);
  assert.deepEqual(originSelectors({ kind: "connector", id: "a-1" }), [{ scope: "board", selector: '[data-id="a-1"]', svgOnly: true }]);
});

test("an id with a quote in it cannot break out of its selector", () => {
  assert.equal(originSelectors({ kind: "person", actorId: 'a"] , body [x="' })[0].selector,
    '.person[data-actor-id="a\\"] , body [x=\\""]');
});

// ----------------------------------------------------------------- coalescer

function fakeFrames() {
  const queue = new Map();
  let next = 1;
  return {
    raf: fn => { const id = next++; queue.set(id, fn); return id; },
    caf: id => { queue.delete(id); },
    get waiting() { return queue.size; },
    tick() { const run = [...queue.values()]; queue.clear(); for (const fn of run) fn(); },
  };
}

test("however often it is asked, the recompute runs once per frame", () => {
  const frames = fakeFrames();
  let runs = 0;
  const c = createCoalescer(() => { runs++; }, frames.raf, frames.caf);
  assert.equal(c.schedule(), true);
  assert.equal(c.schedule(), false);
  c.schedule(); c.schedule();
  assert.equal(frames.waiting, 1, "one frame requested");
  assert.equal(c.pending, true);
  assert.equal(runs, 0, "nothing runs before the frame");
  frames.tick();
  assert.equal(runs, 1);
  assert.equal(c.pending, false);
  frames.tick();
  assert.equal(runs, 1, "and nothing more until asked again");
  c.schedule();
  frames.tick();
  assert.equal(runs, 2);
});

test("a cancelled recompute does not run, and the next request asks for a new frame", () => {
  const frames = fakeFrames();
  let runs = 0;
  const c = createCoalescer(() => { runs++; }, frames.raf, frames.caf);
  c.schedule();
  c.cancel();
  assert.equal(frames.waiting, 0);
  assert.equal(c.pending, false);
  frames.tick();
  assert.equal(runs, 0);
  c.cancel();   // cancelling twice is harmless
  assert.equal(c.schedule(), true);
  frames.tick();
  assert.equal(runs, 1);
});

test("a request made while the recompute runs gets the next frame, not this one", () => {
  const frames = fakeFrames();
  let runs = 0, c;
  c = createCoalescer(() => { runs++; if (runs === 1) c.schedule(); }, frames.raf, frames.caf);
  c.schedule();
  frames.tick();
  assert.equal(runs, 1);
  assert.equal(frames.waiting, 1);
  frames.tick();
  assert.equal(runs, 2);
});

test("a frame handle of 0 still counts as waiting", () => {
  let fn = null, cancelled = null;
  const c = createCoalescer(() => {}, f => { fn = f; return 0; }, id => { cancelled = id; });
  c.schedule();
  assert.equal(c.pending, true);
  c.cancel();
  assert.equal(cancelled, 0);
  assert.ok(fn);
});
