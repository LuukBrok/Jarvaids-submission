/**
 * The parked margin's pure rules, without a browser: which section is the
 * shelf, what parking and unparking send, what refuses a park, and the
 * screen-to-world arithmetic a drag out depends on.
 *
 *     node --test tests/parked-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { accentOf, createPayload, findParked, holderOf, inside, isParkedSection, liveMembers, parkPayload,
  parkedNotes, parkedSections, refusal, shortWords, toWorld, unparkPayload, unparkPoint, withPending,
  PARKED_SIZE } from "../tools/parked.mjs";

const note = (id, extra = {}, position = null) => ({ id, kind: "item", revision: 1, position,
  data: { item_kind: "content", status: "accepted", origin: "human", text: `note ${id}`, refs: [], ...extra } });
const proposal = (id, extra = {}) => ({ id, kind: "proposal", revision: 1, position: null,
  data: { proposal_kind: "content", status: "needs_review", origin: "human", text: id, refs: [], ...extra } });
const section = (id, extra = {}, revision = 3) => ({ id, kind: "item", revision, position: { x: 900, y: 0, w: 200, h: 400, revision: 1 },
  data: { item_kind: "section", status: "accepted", origin: "human", made_by_hand: true, author_id: "a1",
    title: "Parked", form: "free", member_ids: [], created_at: 100, ...extra } });
const cluster = (id, members) => ({ id, kind: "item", revision: 1,
  data: { item_kind: "relationship", form: "cluster", status: "accepted", text: "Onboarding", refs: members.map(m => ({ id: m, revision: 1 })) } });
const snap = records => ({ actor_id: "a1", records, session: { state: "active" } });

test("the shelf is a hand-made, accepted, free section titled Parked", () => {
  assert.equal(isParkedSection(section("s")), true);
  for (const [why, extra] of [
    ["another title", { title: "Risks" }], ["title in other case", { title: "parked" }], ["another form", { form: "cluster" }],
    ["removed", { status: "undone" }], ["a model's", { origin: "model", made_by_hand: false }],
  ]) assert.equal(isParkedSection(section("s", extra)), false, why);
  assert.equal(isParkedSection({ ...section("p"), kind: "proposal" }), false, "a proposal is not the shelf");
});

test("findParked returns the oldest Parked section, then the lowest id, and null before first use", () => {
  assert.equal(findParked(snap([note("n1")])), null);
  const s = snap([section("b", { created_at: 200 }), section("z", { created_at: 100 }), section("a", { created_at: 100 }),
    section("r", { title: "Risks", created_at: 1 })]);
  assert.equal(findParked(s).id, "a");
  assert.deepEqual(parkedSections(s).map(r => r.id), ["a", "z", "b"]);
});

test("parked notes are the accepted notes on any Parked section, in shelf order", () => {
  const s = snap([
    note("n1"), note("n2"), note("gone", { status: "undone" }), proposal("p1"),
    section("old", { created_at: 1, member_ids: ["n2", "gone"] }),
    section("new", { created_at: 2, member_ids: ["n1", "p1", "n2"] }),
  ]);
  const parked = parkedNotes(s);
  assert.deepEqual([...parked.keys()], ["n2", "n1"]);
  assert.equal(parked.get("n2").id, "old");
  assert.equal(parked.get("n1").id, "new");
});

test("parking the first note creates the section with that member, right of what is placed", () => {
  const s = snap([note("n1", {}, { x: 100, y: 40, revision: 1 }), note("n2", {}, { x: 600, y: -20, revision: 1 }), note("n3")]);
  const p = createPayload(s, "n3");
  assert.deepEqual(p.data, { title: "Parked", form: "free", member_ids: ["n3"] });
  assert.equal(p.kind, "section");
  assert.deepEqual([p.w, p.h], [PARKED_SIZE.w, PARKED_SIZE.h]);
  assert.deepEqual([p.w, p.h], [200, 400]);
  assert.ok(p.x > 600 + 320, `x ${p.x} clears the widest note at 600`);
  assert.equal(p.y, -20);
  assert.deepEqual([createPayload(snap([note("n1")]), "n1").x, createPayload(snap([note("n1")]), "n1").y], [0, 0]);
});

test("parking adds to the end of member_ids with the section's revision, dropping members no longer on the canvas", () => {
  const shelf = section("s", { member_ids: ["n1", "gone", "n1"] }, 7);
  const s = snap([note("n1"), note("n2"), note("gone", { status: "undone" }), shelf]);
  assert.deepEqual(liveMembers(s, shelf), ["n1"]);
  assert.deepEqual(parkPayload(s, shelf, "n2"), { item_id: "s", expected_revision: 7, data: { member_ids: ["n1", "n2"] } });
  assert.equal(parkPayload(s, shelf, "n1"), null, "already parked");
});

test("unparking removes the note and keeps the rest in order", () => {
  const shelf = section("s", { member_ids: ["n1", "n2", "n3"] }, 4);
  const s = snap([note("n1"), note("n2"), note("n3"), shelf]);
  assert.deepEqual(unparkPayload(s, shelf, "n2"), { item_id: "s", expected_revision: 4, data: { member_ids: ["n1", "n3"] } });
  assert.deepEqual(unparkPayload(s, shelf, "n1").data.member_ids, ["n2", "n3"]);
  assert.equal(unparkPayload(s, shelf, "elsewhere"), null);
});

test("a note in a group or another section, or one not accepted, is refused", () => {
  const s = snap([note("free"), note("grouped"), note("sectioned"), proposal("proposed"), note("onShelf"),
    cluster("c1", ["grouped"]), section("risks", { title: "Risks", member_ids: ["sectioned"] }),
    section("shelf", { member_ids: ["onShelf"] })]);
  assert.equal(refusal(s, "free"), null);
  assert.equal(refusal(s, "onShelf"), null, "the shelf itself is not another section");
  assert.equal(holderOf(s, "grouped").kind, "group");
  assert.equal(holderOf(s, "sectioned").kind, "section");
  assert.match(refusal(s, "grouped"), /^Take the note out of its group first/);
  assert.match(refusal(s, "sectioned"), /^Take the note out of its group first/);
  assert.match(refusal(s, "proposed"), /Only accepted notes/);
  assert.match(refusal(s, "missing"), /no longer on the canvas/);
});

test("pending writes show at once, and the snapshot wins once they are cleared", () => {
  const base = new Map([["a", { id: "s" }]]);
  assert.deepEqual([...withPending(base, new Map([["b", true]])).keys()], ["a", "b"]);
  assert.deepEqual([...withPending(base, new Map([["a", false]])).keys()], []);
  assert.deepEqual([...withPending(base, new Map()).keys()], ["a"]);
  assert.equal(base.size, 1, "the snapshot's map is not changed");
});

test("world coordinates: (client - board - pan) / zoom", () => {
  const rect = { left: 100, top: 50 };
  assert.deepEqual(toWorld(100, 50, rect, { x: 0, y: 0, z: 1 }), { x: 0, y: 0 });
  assert.deepEqual(toWorld(340, 250, rect, { x: 40, y: 0, z: 2 }), { x: 100, y: 100 });
  assert.deepEqual(toWorld(150, 75, rect, { x: -50, y: -25, z: 0.5 }), { x: 200, y: 100 });
  // Round trip: the world point drawn back on screen is where the pointer was.
  const view = { x: 37, y: -12, z: 1.2 }, w = toWorld(612, 433, rect, view);
  assert.ok(Math.abs(rect.left + view.x + w.x * view.z - 612) < 1e-9);
  assert.ok(Math.abs(rect.top + view.y + w.y * view.z - 433) < 1e-9);
});

test("an unparked note lands left of the band, level with its card, inside the board", () => {
  const boardRect = { left: 0, top: 100, right: 1000, bottom: 700 };
  const bandRect = { left: 800, top: 100, right: 1000, bottom: 700 };
  assert.deepEqual(unparkPoint(boardRect, bandRect, { top: 300 }), { x: 800 - 24 - 320, y: 300 });
  assert.equal(unparkPoint(boardRect, bandRect, { top: 690 }).y, 700 - 24 - 120, "kept above the board's bottom");
  assert.equal(unparkPoint(boardRect, bandRect, { top: 0 }).y, 124, "kept below the board's top");
  // Under the board (narrow layout): not left of it, inside the board instead.
  const below = unparkPoint(boardRect, { left: 0, top: 712, right: 1000, bottom: 900 }, { top: 760 });
  assert.ok(below.x >= 24 && below.y <= 700 - 24, JSON.stringify(below));
});

test("small helpers: inside, accentOf, shortWords", () => {
  const r = { left: 10, top: 10, right: 20, bottom: 20, width: 10, height: 10 };
  assert.equal(inside(r, 15, 15), true);
  assert.equal(inside(r, 21, 15), false);
  assert.equal(inside({ ...r, width: 0 }, 15, 15), false, "a hidden band holds nothing");
  assert.equal(accentOf(["note", "item-accepted", "note-mint"]), "mint");
  assert.equal(accentOf(["note-head", "note-dragging"]), null);
  assert.equal(shortWords("  a   b "), "a b");
  assert.equal(shortWords("x".repeat(60), 10).length, 10);
});
