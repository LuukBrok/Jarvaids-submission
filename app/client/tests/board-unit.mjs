/**
 * The board's pure rules, without a browser.
 *
 * boardModel decides what the canvas and the list both show, so a mistake
 * here is a mistake in two views at once. These run in Node in a second.
 *
 *     node --test tests/board-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ACCENTS, parseColour } from "../canvas-objects.mjs";
import { acceptedStamp, boardModel, hullBox, isCorrected, machineMade, noteAccent, noteMeta, noteKind, noteRotation,
  widthStep } from "../board.mjs";

const item = (id, extra = {}) => ({ id, kind: "item", revision: 1,
  data: { item_kind: "content", status: "accepted", origin: "human", text: id, accepted_by: "a1", refs: [], ...extra } });
const proposal = (id, extra = {}) => ({ id, kind: "proposal", revision: 1,
  data: { proposal_kind: "content", status: "needs_review", origin: "human", text: id, author_id: "a1", refs: [], ...extra } });
const cluster = (id, members, status = "accepted") => ({ id, kind: "item", revision: 1,
  data: { item_kind: "relationship", form: "cluster", status, text: "Onboarding", refs: members.map(m => ({ id: m, revision: 1 })) } });
const snap = records => ({ records, members: [{ id: "a1", name: "Sanne" }], board_order: records.map(r => r.id) });

test("the board holds accepted content and open content proposals, nothing else", () => {
  const s = snap([
    item("kept"), item("undone", { status: "undone" }),
    proposal("open"), proposal("stale", { status: "stale" }),
    proposal("rejected", { status: "rejected" }), proposal("accepted", { status: "accepted" }),
    { id: "seg", kind: "transcript_segment", revision: 1, data: { status: "final" } },
    cluster("group", ["kept"]),
  ]);
  assert.deepEqual(boardModel(s).notes.map(n => n.id), ["kept", "open", "stale"]);
});

test("a group is not drawn as a note, and its members know their group", () => {
  const s = snap([item("a"), item("b"), item("c"), cluster("g", ["a", "b"])]);
  const model = boardModel(s);
  assert.deepEqual(model.clusters.map(c => c.id), ["g"]);
  assert.equal(model.groupOf.get("a").id, "g");
  assert.equal(model.groupOf.get("c"), undefined);
  assert.ok(!model.notes.some(n => n.id === "g"));
});

test("an undone group releases its members", () => {
  const model = boardModel(snap([item("a"), cluster("g", ["a"], "undone")]));
  assert.equal(model.groupOf.size, 0);
  assert.equal(model.clusters.length, 0);
});

test("a proposed group is provisional and separate from accepted groups", () => {
  const proposed = { id: "pg", kind: "proposal", revision: 1, data: { proposal_kind: "relationship", form: "cluster",
    status: "needs_review", origin: "human", text: "Maybe", refs: [{ id: "a", revision: 1 }] } };
  const model = boardModel(snap([item("a"), proposed]));
  assert.deepEqual(model.proposedClusters.map(c => c.id), ["pg"]);
  assert.equal(model.groupOf.size, 0, "a proposal must not make anything a member");
});

test("only the human origin counts as written by a person", () => {
  for (const origin of ["fixture", "model", "anything-new"]) assert.ok(machineMade(proposal("p", { origin })), origin);
  assert.ok(!machineMade(proposal("p", { origin: "human" })));
});

test("the collapsed line never hides that a reading is a stand-in or needs review", () => {
  const s = snap([]);
  s.members = [{ id: "a1", name: "Sanne" }];
  assert.match(noteMeta(s, proposal("p", { origin: "fixture", synthetic: true })), /Stand-in reading, needs review/);
  assert.match(noteMeta(s, proposal("p", { origin: "model", synthetic: false, provider: "ocr-x" })), /Read by Ocr-x, needs review/);
  assert.match(noteMeta(s, proposal("p", { status: "stale" })), /source changed/);
  assert.equal(noteMeta(s, item("i")), "Accepted by Sanne");
  assert.equal(noteMeta(s, proposal("p")), "Typed by Sanne, not yet reviewed");
});

test("a reading keeps saying it came from a photograph after a person retyped it", () => {
  assert.equal(noteKind(proposal("p", { origin: "fixture", region_id: "region_001" })), "Note · from photograph");
  assert.equal(noteKind(item("i", { origin: "human", region_id: "region_001" })), "Note · retyped from photograph");
  assert.equal(noteKind(item("i")), "Note · typed");
});

test("a proposed note's angle comes from its id, within 1.5 degrees, never so small it reads straight", () => {
  const ids = Array.from({ length: 400 }, (_, i) => `prop_${i.toString(16)}`);
  for (const id of ids) {
    const a = noteRotation(id);
    assert.ok(Math.abs(a) <= 1.5 && Math.abs(a) >= 0.4, `${id}: ${a}`);
    assert.equal(noteRotation(id), a, "the same id, the same angle, on every screen");
  }
  const signs = new Set(ids.map(id => Math.sign(noteRotation(id))));
  assert.deepEqual([...signs].sort(), [-1, 1], "askew both ways across a wall");
});

test("a corrected note: retyped from the photograph, or a model's accepted text edited since", () => {
  assert.ok(isCorrected(proposal("p", { origin: "fixture", region_id: "r1", reading_status: "human_transcribed" })));
  assert.ok(isCorrected({ ...item("i", { origin: "model", region_id: "r1" }), revision: 2 }));
  assert.ok(!isCorrected(item("i", { origin: "model", region_id: "r1" })), "accepted as read");
  assert.ok(!isCorrected({ ...item("i"), revision: 3 }), "a person's own note edited is not a correction of a model");
});

test("a note's colour is evidence: a photographed note takes its paper's accent, anything else is yellow", () => {
  // Read from tokens.css, so no colour is repeated here.
  const css = readFileSync(new URL("../tokens.css", import.meta.url), "utf8");
  const palette = Object.fromEntries(ACCENTS.map(n => [n, parseColour(css.match(new RegExp(`--${n}:\\s*([^;]+);`))?.[1])]));
  const paper = (name, shift) => "#" + palette[name].map(v => Math.max(0, Math.min(255, v + shift)).toString(16).padStart(2, "0")).join("");
  assert.equal(noteAccent(proposal("p", { origin: "fixture", region_id: "r1", colour: { hex: paper("mint", -8) } }), palette), "mint");
  assert.equal(noteAccent(item("i", { origin: "model", region_id: "r1", colour: { hex: paper("periwinkle", -6) } }), palette), "periwinkle");
  assert.equal(noteAccent(proposal("typed"), palette), "yellow", "typed");
  assert.equal(noteAccent(proposal("p", { origin: "fixture", region_id: "r1", colour: null }), palette), "yellow", "colour not measured");
});

test("a group's rectangle holds its label inside, above the members", () => {
  const box = hullBox([{ x: 0, y: 100, w: 200, h: 80 }, { x: 260, y: 120, w: 200, h: 80 }]);
  assert.deepEqual(box, { x: -16, y: 100 - 16 - 32, w: 460 + 32, h: 200 + 16 - (100 - 16 - 32), outline: "rect" });
  assert.equal(hullBox([]), null);
});

test("the accepted stamp says who and when", () => {
  const s = snap([]);
  const at = new Date(2026, 9, 20, 14, 2).getTime() / 1000;
  assert.equal(acceptedStamp(s, item("i", { created_at: at })), "Accepted by Sanne 14:02");
  assert.equal(acceptedStamp(s, item("i")), "Accepted by Sanne", "no time when the record has none");
});

test("width steps follow canvas-layout.md: 24 and 90 characters", () => {
  assert.equal(widthStep("x".repeat(24)), "narrow");
  assert.equal(widthStep("x".repeat(25)), "default");
  assert.equal(widthStep("x".repeat(90)), "default");
  assert.equal(widthStep("x".repeat(91)), "wide");
});
