/**
 * The canvas: a pannable, zoomable board of notes, groups and drawings on a
 * dotted paper ground (DESIGN.md 1.1 to 1.3).
 *
 * What it draws, and the rule each drawing follows:
 *
 *   Proposed notes          soft yellow, a yellow left edge, askew by up to
 *                           1.5 degrees (deterministic from the id) and a mono
 *                           "Proposed". A model made them; nobody accepted.
 *   Typed, not reviewed     paper with a hairline edge and "Not yet reviewed".
 *                           A person wrote it, so it is not a guess, but
 *                           nobody has accepted it into the record either.
 *   Accepted notes          their accent at full strength, straight, with a
 *                           mono stamp of who accepted them and when. A note
 *                           read from a photograph takes the accent nearest
 *                           its measured paper colour; a typed note is yellow.
 *   Corrected notes         a 6px ink mark in the corner: a person retyped
 *                           what a model read.
 *   Groups and sections     a soft rectangle behind the members with a Small
 *                           label inside its top left, askew by one degree
 *                           while proposed, straight once accepted.
 *
 * On a touch screen the board is read only: a phone in the room reads and
 * reviews, it does not rearrange the shared canvas by accident.
 *
 * Two things here are local to this screen and are never saved:
 *
 *   The view (pan and zoom), because one person zooming must not move the
 *   shared display.
 *
 *   Open details (F3.8, spec/expandable-notes.md). Opening a note pushes the
 *   notes below it down by display offsets that are recomputed from saved
 *   geometry on every render, so repeated toggling cannot drift and nothing is
 *   ever sent to item.place. Moving a note that is open or pushed is refused
 *   until details are closed, so an offset can never be saved as a move.
 *
 * Moving a note is not agreeing with it: a drag goes to item.place with no
 * review. Dropping a note inside an accepted group's hull adds it to that
 * group, and dragging it out removes it, both without review, because
 * cluster.membership is a person's arrangement act just as a move is.
 *
 * The other canvas objects (canvas-objects.mjs):
 *
 *   Sections                a soft area with "Section · title" inside, drawn
 *                           under everything, so its members sit on it.
 *   Shapes                  flat full-strength fields with words in the Note
 *                           style; text objects are type alone, in ink.
 *   Connectors and strokes  one SVG layer under the notes. A person's are the
 *                           human mark (ink at 85%); a proposed one is the
 *                           machine mark (dashed). A connector is a cubic curve
 *                           between the nearest sides of the boxes it joins, so
 *                           it follows a note pushed by open details, and is
 *                           not drawn when an end is gone. It has a head only
 *                           when this device knows it is directed.
 *   Any canvas proposal     no fill, the machine mark and "Proposed".
 *
 * None of them take pointer events, so a press on one pans the board and a
 * note above one still drags. The tools (tools/draw.mjs, tools/connect.mjs)
 * work through setTool, setToolHandler, hold and decorate below; only while
 * the eraser is the tool do strokes and connectors take a press.
 */
import { pollElement } from "./polls.mjs";
import { topicGroups, layoutTopicGroups } from "./topic-layout.mjs";
import { documentElement } from "./documents.mjs";
import { collectingCalendar, dateChip, dateChipElement, eventText, noteEvents } from "./chips.mjs";
import { ACCENTS, aliasAccepted, arrowEnds, canvasObject, connectorGeometry, connectorHead, nearestAccent,
  objectBox, objectName, shortText, strokeBounds, strokePath, toneOf } from "./canvas-objects.mjs";

const HULL_PAD = 16;          // a group's rectangle sits 16px outside its members
const HULL_HEAD = 32;         // and is 32px taller at the top, for its label
const LANE_GAP = 24;          // vertical gap in the "not placed yet" lane
const LANE_WIDTH = 320 + 48;  // the widest note (--note-w-wide) plus a gutter
const DETAIL_GAP = 8;
const ZOOM_MIN = 0.25, ZOOM_MAX = 2;
const SVG_NS = "http://www.w3.org/2000/svg";
/** Bottom to top: a section is under what sits on it, and an arrow is drawn
 * last because it ends at the others' boxes. */
const DRAW_ORDER = ["section", "shape", "text", "stroke", "arrow"];

function svg(name, attributes = {}) {
  const el = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, String(value));
  return el;
}

/** canvas-layout.md section 1: three width steps, never free sizing. */
export function widthStep(text) {
  const n = (text ?? "").length;
  return n <= 24 ? "narrow" : n <= 90 ? "default" : "wide";
}

/** The server's origins are `human`, `fixture` and `model`. Only the first was
 * written by a person, so the test is "not human" rather than a list of
 * machine names that would silently miss the next adapter. */
export function machineMade(record) {
  return record.data.origin !== "human";
}

export function isCluster(record) {
  return record.data.form === "cluster";
}

/**
 * How far a proposed note sits askew, in degrees: from its id, so every
 * screen draws the same note at the same angle and a re-render never makes
 * it wobble. Between 0.4 and 1.5 degrees either way: under 0.4 a note reads
 * as straight, which is the accepted look.
 */
export function noteRotation(id) {
  let h = 0x811c9dc5;
  for (const c of String(id ?? "")) { h ^= c.codePointAt(0); h = Math.imul(h, 0x01000193) >>> 0; }
  const magnitude = 0.4 + ((h >>> 1) % 1000) / 1000 * 1.1;
  return Math.round((h & 1 ? -magnitude : magnitude) * 100) / 100;
}

/** A note a person corrected: retyped from the photograph, or a model's
 * reading whose accepted text was edited since (its revision moved on). */
export function isCorrected(record) {
  const d = record?.data ?? {};
  if (d.summary_topic_id) return Boolean(d.last_editor);
  if (d.reading_status === "human_transcribed") return true;
  return record?.kind === "item" && machineMade(record) && Number(record.revision) > 1;
}

/** The accent a note is drawn in. A note's colour is evidence: one read from a
 * photograph takes the accent nearest its measured paper colour; anything
 * else is yellow. A quote note's fill is set by the quote tool through
 * --note-fill, which wins over this. */
export function noteAccent(record, palette) {
  const hex = record?.data?.colour?.hex;
  if (!record?.data?.region_id || !hex) return "yellow";
  return nearestAccent(hex, palette);
}

/** The five accents as tokens.css defines them, read from the page, so the
 * nearest-colour rule never repeats a literal. Null until the page has them
 * (before the stylesheet loads). Shared by the board and the photo flow's
 * found list, which draw the same note in the same colour. */
export function accentPalette() {
  if (typeof document === "undefined") return null;
  const style = getComputedStyle(document.documentElement);
  const palette = Object.fromEntries(ACCENTS.map(name => [name, style.getPropertyValue(`--${name}`).trim()]));
  return Object.values(palette).every(Boolean) ? palette : null;
}

/** The rectangle of a group drawn round its members' boxes: HULL_PAD outside
 * them, with HULL_HEAD more at the top so the label sits inside the
 * rectangle, never above it where the board's edge would cut it off. */
export function hullBox(boxes) {
  if (!boxes.length) return null;
  const x = Math.min(...boxes.map(b => b.x)) - HULL_PAD, y = Math.min(...boxes.map(b => b.y)) - HULL_PAD - HULL_HEAD;
  const w = Math.max(...boxes.map(b => b.x + b.w)) + HULL_PAD - x, h = Math.max(...boxes.map(b => b.y + b.h)) + HULL_PAD - y;
  return { x, y, w, h, outline: "rect" };
}

/** What the board holds, derived from one snapshot. Pure, so the list view and
 * the canvas cannot disagree about what is on the board. */
export function boardModel(snapshot) {
  const records = snapshot?.records ?? [];
  const open = r => ["needs_review", "stale"].includes(r.data.status);
  const notes = records.filter(r =>
    (r.kind === "item" && r.data.status === "accepted" && !isCluster(r) && r.data.item_kind === "content") ||
    (r.kind === "proposal" && r.data.proposal_kind === "content" && open(r)));
  const clusters = records.filter(r => r.kind === "item" && isCluster(r) && r.data.status === "accepted");
  const proposedClusters = records.filter(r => r.kind === "proposal" && r.data.proposal_kind === "relationship" &&
    r.data.form === "cluster" && open(r));
  const groupOf = new Map();
  for (const c of clusters) for (const ref of c.data.refs) groupOf.set(ref.id, c);
  const objects = records.map(canvasObject).filter(Boolean);

  const rank = new Map((snapshot?.board_order ?? []).map((id, i) => [id, i]));
  const byRank = (a, b) => (rank.get(a.id) ?? -1) - (rank.get(b.id) ?? -1);
  notes.sort(byRank);
  // Kind first, so sections are drawn before (under) what sits on them.
  objects.sort((a, b) => DRAW_ORDER.indexOf(a.kind) - DRAW_ORDER.indexOf(b.kind) || byRank(a, b));

  /** What something on the canvas is called in a sentence, or null when it is
   * not on the canvas: an arrow's ends and a section's members are named, and
   * counted, from what is actually drawn. */
  const names = new Map();
  for (const n of notes) names.set(n.id, quoted(n.data.text));
  for (const c of [...clusters, ...proposedClusters]) names.set(c.id, `the group ${quoted(c.data.text)}`);
  for (const o of objects) if (o.kind !== "arrow") names.set(o.id, objectName(o));
  const nameOf = id => names.get(id) ?? null;
  return { notes, clusters, proposedClusters, groupOf, objects, nameOf,
    polls: records.filter(r => r.kind === "poll"), documents: records.filter(r => r.kind === "command_document") };
}

const quoted = text => `“${shortText(text)}”`;

/** The one line under an object in the list. Made by hand is said as such,
 * because nobody reviewed it: drawing is arranging, like a move. */
export function objectMeta(snapshot, obj) {
  const d = obj.record.data;
  if (obj.proposed) {
    const stale = d.status === "stale" ? ". Its source changed" : "";
    const by = machineMade(obj.record) ? readerName(d) : memberName(snapshot, d.author_id);
    return `Proposed by ${by}, needs review${stale}`;
  }
  if (d.made_by_hand) return `${obj.kind === "text" ? "Written" : "Drawn"} by ${memberName(snapshot, d.author_id ?? d.accepted_by)}`;
  return `Accepted by ${memberName(snapshot, d.accepted_by)}`;
}

/** How a reader is named on screen. The server's provider ids are lower case
 * machine names; a person reads "Claude", and a stand-in says it is one. */
export function readerName(data) {
  if (data.synthetic || data.provider === "fixture") return "the stand-in reader";
  const p = data.provider ?? data.origin ?? "a model";
  return p.charAt(0).toUpperCase() + p.slice(1);
}

export function memberName(snapshot, actorId) {
  return snapshot?.members?.find(m => m.id === actorId)?.name ?? "someone";
}

/** The one line under a collapsed note. Status is never hidden behind
 * expansion, so it lives here, not in the details. */
export function noteMeta(snapshot, r) {
  if (r.data.summary_topic_id) return "AI summary · " + (r.data.last_editor ? "corrected by the team" : "added automatically");
  if (r.data.automatic) return machineMade(r) ? (r.data.synthetic ? "Stand-in reading · added automatically" : "AI reading · added automatically") : "Added automatically";
  if (r.kind === "item") return `Accepted by ${memberName(snapshot, r.data.accepted_by)}`;
  const stale = r.data.status === "stale" ? ". Its source changed" : "";
  if (machineMade(r)) {
    return (r.data.synthetic ? "Stand-in reading, needs review" : `Read by ${readerName(r.data)}, needs review`) + stale;
  }
  return `Typed by ${memberName(snapshot, r.data.author_id)}, not yet reviewed` + stale;
}

/** The accepted note's stamp: who accepted it and, when the record says, at
 * what time ("Accepted by Sam 14:02"). The item is made at acceptance, so its
 * created_at is the moment of accepting. */
export function acceptedStamp(snapshot, r) {
  const t = Number(r.data.created_at);
  if (!Number.isFinite(t) || t <= 0) return noteMeta(snapshot, r);
  const time = new Date(t * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${noteMeta(snapshot, r)} ${time}`;
}

export function noteKind(r) {
  if (r.data.summary_topic_id) return "Summary · AI";
  if (r.data.region_id && machineMade(r)) return "Note · from photograph";
  if (r.data.region_id) return "Note · retyped from photograph";
  return "Note · typed";
}

/** Wall reading order for notes that land together: by the region they were
 * read from (the photo flow numbers regions as they were marked), then by the
 * board's own order. */
const readingOrder = rank => (a, b) =>
  String(a.data.region_id ?? "~").localeCompare(String(b.data.region_id ?? "~")) || (rank.get(a.id) ?? 0) - (rank.get(b.id) ?? 0);

export class Board {
  /**
   * @param {HTMLElement} root   the board viewport
   * @param {object} hooks       { send, review, crop, revoke, attention, onSelection, onZoom }
   */
  constructor(root, hooks) {
    this.root = root;
    this.hooks = hooks;
    this.world = document.createElement("div");
    this.world.className = "world";
    this.root.append(this.world);
    this.view = { x: 40, y: 40, z: 1, touched: false };
    this.expanded = new Set();
    this.selected = new Set();
    this.snapshot = null;
    this.busy = false;        // a drag, pan or tool gesture in progress: renders wait
    this.holds = 0;           // a tool holding the drawing still (an open label field)
    this.dirty = false;
    this.cropUrls = new Map(); // note id -> blob URL, revoked on collapse
    this.cropSizes = new Map();
    this.readonly = window.matchMedia?.("(pointer: coarse)").matches ?? false;
    // The tools. `tool` is the active one; a handler is registered per tool
    // name by tools/draw.mjs and tools/connect.mjs.
    this.tool = "select";
    this.root.dataset.tool = "select";
    this.toolHandlers = new Map();
    this.decorators = [];
    // Which connectors are directed: kept on this device by tools/connect.mjs.
    this.directed = new Set();
    // The motion helper (ctx.settle), given by the dock at mount. Without it
    // the board draws every change at once, which is also what reduced motion
    // gives.
    this.settle = null;
    this.seen = null;          // id -> how each note looked at the last render
    this.lastEls = new Map();  // id -> the note element from the last render
    this.boxes = new Map();    // id -> displayed box, from the last render
    this.placed = new Map();   // id -> where a person just dropped it, until the server agrees
    this.hitBoxes = [];        // shapes and text, topmost last, for the connector
    this.grid = parseFloat(getComputedStyle(root).getPropertyValue("--space-5")) || 24;
    this.pollDrafts = new Map();
    this.documentDrafts = new Map();
    this.documentFocus = new Map();
    this.seenPolls = new Set();
    this.layoutMode = "topics";
    this.openCommands = new Set();
    this.#wireViewport();
    new ResizeObserver(() => {
      if (this.snapshot && this.isTopicLayout() && !this.busy && !this.holds) {
        this.view.touched = false;
        this.render(this.snapshot);
      }
    }).observe(root);
  }

  // ------------------------------------------------------------- view state

  #apply() {
    const { x, y, z } = this.view;
    this.world.style.transform = `translate(${x}px, ${y}px) scale(${z})`;
    // The dots move and scale with the world, so the ground reads as the
    // paper the notes are on. Below half size the spacing doubles, so the
    // dots never crowd into a tone.
    let step = this.grid * z;
    while (step < this.grid / 2) step *= 2;
    this.root.style.setProperty("--grid-size", `${step}px`);
    this.root.style.setProperty("--grid-x", `${x}px`);
    this.root.style.setProperty("--grid-y", `${y}px`);
    this.hooks.onZoom?.(z);
  }

  zoomAt(factor, cx, cy) {
    const { x, y, z } = this.view;
    const next = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z * factor));
    // Keep the world point under (cx, cy) where it is.
    this.view.x = cx - (cx - x) * (next / z);
    this.view.y = cy - (cy - y) * (next / z);
    this.view.z = next;
    this.view.touched = true;
    this.#apply();
  }

  zoomBy(factor) {
    const r = this.root.getBoundingClientRect();
    this.zoomAt(factor, r.width / 2, r.height / 2);
  }

  panBy(dx, dy) {
    this.view.x += dx; this.view.y += dy; this.view.touched = true;
    this.#apply();
  }

  /** The projector setting's scale (--scale on the page, 1 or 1.25). The
   * canvas's type does not follow --scale (tokens.css, --fs-canvas-*), so
   * the board carries it as zoom instead: grown type at fixed note places
   * ran each note into the next (phase 5 review). */
  roomZoom() {
    return parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--scale")) || 1;
  }

  /** Fit everything drawn, never zooming in past 100% (125% with the
   * projector setting on, roomZoom). Only what is shown
   * counts: a parked note and the Parked section are hidden by the parked
   * tool (display: none), and fitting them would leave an empty stretch of
   * board where they were. While the parked band lies over the board's right
   * edge, the fit leaves that strip free, and it leaves the floating dock's
   * height free at the bottom, so nothing is fitted under either. */
  fit() {
    const shown = el => el.getClientRects().length > 0;
    const hiddenIds = new Set([...this.world.querySelectorAll(".links [data-id]")].filter(el => !shown(el)).map(el => el.dataset.id));
    const boxes = [...this.world.querySelectorAll(".note:not(.note-ghost):not(.topic-command .note), .topic-command, .hull, .lane-label, .cobj")].filter(shown)
      .map(el => this.#displayed(el))
      .concat((this.linkBounds ?? []).filter(b => !hiddenIds.has(b.id)));
    if (!boxes.length) { this.view = { x: 40, y: 40, z: this.roomZoom(), touched: this.view.touched }; this.#apply(); return; }
    const minX = Math.min(...boxes.map(b => b.x)), minY = Math.min(...boxes.map(b => b.y));
    const maxX = Math.max(...boxes.map(b => b.x + b.w)), maxY = Math.max(...boxes.map(b => b.y + b.h));
    const r = this.root.getBoundingClientRect(), margin = this.isTopicLayout() ? 72 : 40;
    const width = r.width - this.#inset(r, "parked", "right");
    const height = r.height - this.#inset(r, "dock", "bottom");
    const z = Math.min(this.roomZoom(), Math.max(ZOOM_MIN, Math.min((width - 2 * margin) / (maxX - minX || 1),
                                                       (height - 2 * margin) / (maxY - minY || 1))));
    this.view.z = z;
    this.view.x = margin - minX * z + Math.max(0, (width - 2 * margin - (maxX - minX) * z) / 2);
    this.view.y = margin - minY * z;
    this.#apply();
  }

  /** How much of the board's right or bottom edge an element laid over it
   * covers: the parked band (right) on a wide screen, the dock (bottom).
   * Under 1024px the band is a shelf below the board and covers nothing.
   * Read from the page, so the board knows the tools only by their ids. */
  #inset(r, id, side) {
    const el = document.getElementById(id);
    if (!el || el.hidden) return 0;
    const b = el.getBoundingClientRect();
    const over = b.width > 0 && b.height > 0 && b.left < r.right && b.right > r.left && b.top < r.bottom && b.bottom > r.top;
    if (!over) return 0;
    return side === "right" ? (b.left > r.left ? r.right - b.left : 0) : (b.top > r.top ? r.bottom - b.top : 0);
  }

  /** A point on the screen as a point in the world. */
  toWorld(clientX, clientY) {
    const r = this.root.getBoundingClientRect();
    return { x: (clientX - r.left - this.view.x) / this.view.z, y: (clientY - r.top - this.view.y) / this.view.z };
  }

  /** The displayed box of a note, group, shape, text, section or stroke from
   * the last render, or null. */
  boxOf(id) {
    return this.boxes.get(id) ?? null;
  }

  /** The topmost shape or text whose box holds a world point. Shapes take no
   * pointer events (a press on one pans), so the connector finds them by
   * geometry. Sections are areas, not things to connect, so they are not
   * hit. */
  objectAt(point) {
    for (let i = this.hitBoxes.length - 1; i >= 0; i--) {
      const { id, box } = this.hitBoxes[i];
      if (point.x >= box.x && point.x <= box.x + box.w && point.y >= box.y && point.y <= box.y + box.h) return id;
    }
    return null;
  }

  /** World-space box of an element as displayed: saved position plus any
   * display offset. offsetWidth/Height ignore the world's scale. */
  #displayed(el) {
    const x = parseFloat(el.style.left) || 0, y = (parseFloat(el.style.top) || 0) + (Number(el.dataset.offset) || 0);
    return { x, y, w: el.offsetWidth, h: el.offsetHeight };
  }

  // ------------------------------------------------------------------ tools

  /** select, draw, erase or connect. On a read-only board only select. Tells
   * the page through a `jv:tool` event on the board, detail {tool}. */
  setTool(name) {
    const next = this.readonly ? "select" : name;
    if (this.tool === next) return;
    this.toolHandlers.get(this.tool)?.leave?.();
    this.tool = next;
    this.root.dataset.tool = next;
    this.toolHandlers.get(next)?.enter?.();
    this.root.dispatchEvent(new CustomEvent("jv:tool", { detail: { tool: next } }));
  }

  /** A tool's pointer handler: {down(event, hit) -> true to take the press,
   * move(event, point), up(event, point), cancel(), hover(event, point),
   * enter(), leave()}. `hit` is {kind: "note" | "object" | "mark" | "empty",
   * id, point}, with world coordinates. */
  setToolHandler(name, handler) {
    this.toolHandlers.set(name, handler);
  }

  /** Keeps the drawing as it is until the returned function is called: a
   * re-render would take an open label field away from under the cursor. */
  hold() {
    this.holds += 1;
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this.holds -= 1;
      if (!this.holds && !this.busy && this.dirty) this.render(this.snapshot);
    };
  }

  /** fn(world, model) runs at the end of every render, so a tool's own marks
   * (a stroke being saved, a connector being drawn) survive a redraw. */
  decorate(fn) {
    this.decorators.push(fn);
  }

  /** The SVG layer a tool draws its unsaved marks on: just above the saved
   * marks and under every note, so a mark looks the same before and after it
   * is saved. Made on demand, because every render starts the world afresh. */
  draftLayer() {
    let layer = this.world.querySelector(":scope > svg.drafts");
    if (layer) return layer;
    layer = svg("svg", { class: "drafts", width: 1, height: 1, "aria-hidden": "true" });
    const links = this.world.querySelector(":scope > .links");
    if (links) links.after(layer);
    else this.world.insertBefore(layer, this.world.querySelector(":scope > .note"));
    return layer;
  }

  #toolPress(event, hit) {
    const handler = this.toolHandlers.get(this.tool);
    if (!handler?.down) return false;
    return Boolean(handler.down(event, { ...hit, point: this.toWorld(event.clientX, event.clientY) }));
  }

  #hitAt(event) {
    const mark = event.target.closest?.("[data-hit]");
    if (mark) return { kind: "mark", id: mark.dataset.hit };
    const id = this.objectAt(this.toWorld(event.clientX, event.clientY));
    return id ? { kind: "object", id } : { kind: "empty", id: null };
  }

  #wireViewport() {
    const root = this.root;
    const pointers = new Map();
    let pan = null, pinch = null, gesture = null;

    root.addEventListener("pointerdown", event => {
      if (event.target.closest(".note, summary, button, a, input, textarea, select")) return;
      // A tool other than select may take a primary press: a stroke, an
      // eraser click, a connector's end. Anything it leaves still pans.
      if (this.tool !== "select" && event.button === 0 && pointers.size === 0 && !gesture &&
          this.#toolPress(event, this.#hitAt(event))) {
        gesture = { id: event.pointerId, handler: this.toolHandlers.get(this.tool) };
        root.setPointerCapture(event.pointerId);
        this.busy = true;
        return;
      }
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      root.setPointerCapture(event.pointerId);
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) };
        pan = null;
      } else {
        pan = { x: event.clientX, y: event.clientY, moved: false };
      }
      this.busy = true;
    });
    root.addEventListener("pointermove", event => {
      if (gesture && event.pointerId === gesture.id) {
        gesture.handler.move?.(event, this.toWorld(event.clientX, event.clientY));
        return;
      }
      if (!pointers.has(event.pointerId)) {
        this.toolHandlers.get(this.tool)?.hover?.(event, this.toWorld(event.clientX, event.clientY));
        return;
      }
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (pinch && pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        const r = root.getBoundingClientRect();
        this.zoomAt(d / pinch.d, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
        pinch.d = d;
      } else if (pan) {
        const dx = event.clientX - pan.x, dy = event.clientY - pan.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) pan.moved = true;
        pan.x = event.clientX; pan.y = event.clientY;
        this.panBy(dx, dy);
      }
    });
    const end = event => {
      if (gesture && event.pointerId === gesture.id) {
        const { handler } = gesture;
        gesture = null;
        if (event.type === "pointercancel") handler.cancel?.();
        else handler.up?.(event, this.toWorld(event.clientX, event.clientY));
        this.#settle();
        return;
      }
      if (!pointers.has(event.pointerId)) return;
      pointers.delete(event.pointerId);
      if (pointers.size < 2) pinch = null;
      if (pointers.size === 0) {
        // A click on empty board, not a pan, clears the selection.
        if (pan && !pan.moved) this.select(null);
        pan = null;
        this.#settle();
      }
    };
    root.addEventListener("pointerup", end);
    root.addEventListener("pointercancel", end);

    root.addEventListener("wheel", event => {
      event.preventDefault();
      const r = root.getBoundingClientRect();
      // A trackpad pinch arrives as a wheel with ctrlKey. A plain wheel pans,
      // which is what a trackpad's two-finger scroll means on a canvas.
      if (event.ctrlKey || event.metaKey) this.zoomAt(Math.exp(-event.deltaY * 0.01), event.clientX - r.left, event.clientY - r.top);
      else this.panBy(-event.deltaX, -event.deltaY);
    }, { passive: false });

    root.addEventListener("keydown", event => {
      if (event.target !== root) return;
      const step = 48;
      const keys = {
        "+": () => this.zoomBy(1.2), "=": () => this.zoomBy(1.2), "-": () => this.zoomBy(1 / 1.2),
        "0": () => this.fit(), ArrowLeft: () => this.panBy(step, 0), ArrowRight: () => this.panBy(-step, 0),
        ArrowUp: () => this.panBy(0, step), ArrowDown: () => this.panBy(0, -step),
        Escape: () => this.select(null),
      };
      if (keys[event.key]) { event.preventDefault(); keys[event.key](); }
    });
  }

  #settle() {
    this.busy = false;
    if (this.dirty && !this.holds) this.render(this.snapshot);
  }

  // -------------------------------------------------------------- selection

  select(id, additive = false) {
    if (id === null) this.selected.clear();
    else if (additive) this.selected.has(id) ? this.selected.delete(id) : this.selected.add(id);
    else { const only = this.selected.size === 1 && this.selected.has(id); this.selected.clear(); if (!only) this.selected.add(id); }
    for (const el of this.world.querySelectorAll(".note[data-id]")) el.classList.toggle("item-selected", this.selected.has(el.dataset.id));
    this.hooks.onSelection?.([...this.selected]);
  }

  // ----------------------------------------------------------------- render

  /** The five accents as tokens.css defines them, read from the page once it
   * has them, so the nearest-colour rule never repeats a literal. */
  #palette() {
    this.palette ??= accentPalette();
    return this.palette ?? {};
  }

  render(snapshot) {
    this.snapshot = snapshot;
    this.readonly = (window.matchMedia?.("(pointer: coarse)").matches ?? false) || snapshot.session?.state === "closed";
    if (this.busy || this.holds) { this.dirty = true; return; }
    this.dirty = false;
    const active = document.activeElement;
    const keepFocus = this.world.contains(active) ? active.dataset.focusKey : null;
    const caret = typeof active?.selectionStart === "number" ? [active.selectionStart, active.selectionEnd] : null;

    const model = boardModel(snapshot);
    this.root.classList.toggle("topic-overview", this.isTopicLayout(snapshot));
    if (this.isTopicLayout(snapshot)) return this.#renderTopics(snapshot, model, keepFocus, caret);
    this.topicTones = null;
    this.topicAssociations = null;
    const focusDocument = model.documents.filter(d => this.documentFocus.get(d.id) !== d.data.focus_request).at(-1);
    const commands = [...model.polls, ...model.documents].sort((a, b) =>
      (a.data.created_at ?? 0) - (b.data.created_at ?? 0) || a.id.localeCompare(b.id));
    const newCommands = commands.filter(p => !this.seenPolls.has(p.id));
    const focusCommand = newCommands.at(-1) ?? focusDocument;
    const ids = new Set(model.notes.map(n => n.id));
    for (const id of [...this.selected]) if (!ids.has(id)) this.selected.delete(id);
    for (const id of [...this.expanded]) if (!ids.has(id)) this.toggle(id, false);

    this.world.textContent = "";
    // Arrows have no place of their own (the client ignores one if sent).
    // Strokes do not move the lane either: a line drawn left of the wall
    // made the lane jump further left and carried the proposals waiting in
    // it off the screen mid-session (phase 5 review). A stroke is a free
    // mark, so it may sit beside the lane.
    const placedXs = [...model.notes.filter(n => n.position).map(n => n.position.x),
      ...model.objects.filter(o => !["arrow", "stroke"].includes(o.kind) && o.record.position).map(o => o.record.position.x)];
    const laneX = (placedXs.length ? Math.min(...placedXs) : LANE_WIDTH) - LANE_WIDTH;

    const els = new Map();
    const lane = [];
    const palette = this.#palette();
    for (const note of model.notes) {
      const el = this.#note(snapshot, note, model, palette);
      const dropped = this.#dropped(note);
      if (dropped) { el.style.left = `${dropped.x}px`; el.style.top = `${dropped.y}px`; }
      else if (note.position) { el.style.left = `${note.position.x}px`; el.style.top = `${note.position.y}px`; }
      else { el.style.left = `${laneX}px`; lane.push(el); }
      this.world.append(el);
      els.set(note.id, el);
    }

    // The lane for notes nobody has placed yet: stacked by measured height,
    // so a long note cannot run into the next one. Not saved anywhere. A
    // canvas object sent without a place (a proposal may be) joins the lane
    // below the notes rather than not being drawn at all.
    let laneY = 0, laneUsed = lane.length > 0;
    if (snapshot.session?.automatic_workspace) {
      let row = 0;
      for (let i = 0; i < lane.length; i++) {
        const column = i % 3;
        if (!column && i) { laneY += row + LANE_GAP; row = 0; }
        lane[i].style.left = `${laneX - (2 - column) * LANE_WIDTH}px`;
        lane[i].style.top = `${laneY}px`; row = Math.max(row, lane[i].offsetHeight);
      }
      laneY += row + LANE_GAP;
    } else for (const el of lane) { el.style.top = `${laneY}px`; laneY += el.offsetHeight + LANE_GAP; }
    const laneSlot = h => { laneUsed = true; const y = laneY; laneY += h + LANE_GAP; return { x: laneX, y }; };

    const commandRow = [];
    for (const command of commands) {
      const el = command.kind === "poll" ? pollElement(snapshot, command, this.hooks, this.pollDrafts)
        : documentElement(snapshot, command, this.hooks, this.documentDrafts);
      this.#drag(el, command);
      const dropped = this.#dropped(command);
      if (dropped || command.position) {
        const point = dropped ?? command.position;
        el.style.left = `${point.x}px`; el.style.top = `${point.y}px`;
      } else commandRow.push(el);
      this.world.append(el); els.set(command.id, el);
    }
    const placed = [...model.notes, ...commands].filter(n => n.position);
    const objectRights = model.objects.filter(o => !["arrow", "stroke"].includes(o.kind) && o.record.position)
      .map(o => o.record.position.x + (o.record.position.w ?? 320));
    let commandX = Math.max(lane.length ? laneX + LANE_WIDTH : 0,
      ...placed.map(n => n.position.x + els.get(n.id).offsetWidth + LANE_GAP), ...objectRights.map(x => x + LANE_GAP));
    for (const el of commandRow) {
      el.style.left = `${commandX}px`; el.style.top = "0px";
      commandX += el.offsetWidth + LANE_GAP;
    }

    this.#displace(els);
    const hulls = [];
    for (const c of model.clusters) { const h = this.#hull(c, els, false); if (h) hulls.push(h); }
    for (const c of model.proposedClusters) { const h = this.#hull(c, els, true); if (h) hulls.push(h); }
    this.#objects(model, els, hulls, laneSlot);

    if (laneUsed) {
      const label = document.createElement("div");
      label.className = "lane-label t-structure";
      label.textContent = snapshot.session?.automatic_workspace ? "Notes" : "Not placed yet";
      // Above where a group's rectangle round the first note would start
      // (its pad and its label row), so the two never print over each other.
      label.style.left = `${snapshot.session?.automatic_workspace && lane.length ? Math.min(...lane.map(el => parseFloat(el.style.left))) : laneX}px`; label.style.top = `${-(HULL_PAD + HULL_HEAD + LANE_GAP)}px`;
      this.world.append(label);
    }

    this.#motion(model, els);

    if (focusCommand && this.root.getBoundingClientRect().width) {
      for (const doc of model.documents) this.documentFocus.set(doc.id, doc.data.focus_request);
      for (const command of commands) this.seenPolls.add(command.id);
      const viewport = this.root.getBoundingClientRect();
      let box = this.#displayed(els.get(focusCommand.id));
      const row = commandRow.map(el => this.#displayed(el));
      if (!focusCommand.position && row.length) {
        const left = Math.min(...row.map(b => b.x)), right = Math.max(...row.map(b => b.x + b.w));
        // Show neighbouring headings together when they remain readable. On a
        // narrow screen focus the new object and leave neighbours a pan away.
        if ((viewport.width - 80) / (right - left) >= (commandRow.some(el => el.classList.contains("calendar-document")) ? 1 : 0.8))
          box = { x: left, y: 0, w: right - left };
      }
      this.view.touched = true;
      const calendar = focusCommand.data.document_type === "calendar";
      this.view.z = calendar ? 1 : Math.min(1, Math.max(ZOOM_MIN, (viewport.width - 80) / box.w));
      this.view.x = (calendar && viewport.width < box.w + 16 ? 8 : (viewport.width - box.w * this.view.z) / 2) - box.x * this.view.z;
      this.view.y = 40 - box.y * this.view.z;
      this.#apply();
    }
    else if (!this.view.touched && (model.notes.length || model.objects.length || commands.length)) this.fit();
    else this.#apply();
    this.hooks.onSelection?.([...this.selected]);
    if (keepFocus) {
      const target = this.world.querySelector(`[data-focus-key="${keepFocus}"]`);
      target?.focus();
      if (caret && target?.setSelectionRange) target.setSelectionRange(...caret);
    }
    for (const fn of this.decorators) {
      try { fn(this.world, model); } catch (error) { console.error("A board decoration failed:", error); }
    }
    this.root.dispatchEvent(new CustomEvent("jv:board-rendered", { detail: { model } }));
    return model;
  }

  isTopicLayout(snapshot = this.snapshot) {
    return this.layoutMode === "topics" && snapshot?.records.some(r => r.kind === "summary_topic");
  }

  toggleLayout() {
    this.layoutMode = this.isTopicLayout() ? "free" : "topics";
    this.view.touched = false;
    this.render(this.snapshot);
  }

  #renderTopics(snapshot, model, keepFocus, caret) {
    const {groups, associations} = topicGroups(snapshot, [...model.notes, ...model.polls, ...model.documents]);
    this.topicAssociations = associations;
    this.topicTones = new Map(groups.flatMap(g => g.items.map(r => [r.id, g.tone])));
    this.world.textContent = "";
    const els = new Map(), sizes = new Map(), palette = this.#palette();
    for (const group of groups) for (const record of group.items) {
      let el;
      if (record.kind === "poll" || record.kind === "command_document") {
        el = document.createElement("details");
        el.className = `topic-command note-${group.tone}`;
        el.dataset.recordId = record.id;
        el.open = this.openCommands.has(record.id);
        const heading = document.createElement("summary");
        const title = document.createElement("strong");
        title.textContent = record.data.title || record.data.question || record.data.document_type;
        const state = document.createElement("span");
        state.textContent = `${record.kind === "poll" ? "Poll" : record.data.document_type} · ${record.data.state || "draft"}`;
        heading.append(title, state);
        el.append(heading);
        const body = record.kind === "poll" ? pollElement(snapshot, record, this.hooks, this.pollDrafts)
          : documentElement(snapshot, record, this.hooks, this.documentDrafts);
        el.append(body);
        el.addEventListener("toggle", () => {
          if (this.openCommands.has(record.id) === el.open) return;
          if (el.open) this.openCommands.add(record.id); else this.openCommands.delete(record.id);
          if (el.open) this.topicFocusId = record.id;
          this.render(this.snapshot);
        });
      } else {
        el = this.#note(snapshot, record, model, palette);
        el.classList.add("topic-card");
        el.dataset.expanded = String(this.expanded.has(record.id));
      }
      this.world.append(el); els.set(record.id, el);
      sizes.set(record.id, {w: el.offsetWidth, h: el.offsetHeight});
    }
    const viewport = this.root.getBoundingClientRect();
    const layout = layoutTopicGroups(groups, sizes, viewport);
    const hulls = [];
    for (const group of layout.groups) {
      const el = document.createElement("section");
      el.className = `hull topic-group note-${group.tone}`;
      el.setAttribute("aria-label", group.label);
      Object.assign(el.style, {left:`${group.x}px`, top:`${group.y}px`, width:`${group.w}px`, height:`${group.h}px`});
      const title = document.createElement("button");
      title.type = "button"; title.className = "topic-heading";
      title.setAttribute("aria-label", `Focus ${group.label}`);
      title.textContent = `${group.label} · ${group.items.length}`;
      title.addEventListener("click", () => {
        const r = this.root.getBoundingClientRect(), margin = 32;
        const z = Math.min(1, (r.width - 2*margin)/group.w, (r.height - 120)/group.h);
        this.view = {x:(r.width-group.w*z)/2-group.x*z, y:margin-group.y*z, z, touched:true}; this.#apply();
      });
      el.append(title);
      hulls.push({id:group.id, el, box:{x:group.x,y:group.y,w:group.w,h:group.h}});
      for (const p of group.placements) Object.assign(els.get(p.id).style, {left:`${p.x}px`,top:`${p.y}px`});
    }
    this.#objects({...model, objects:model.objects.filter(o => o.kind === "arrow")}, els, hulls, () => ({x:0,y:0}));
    const parked = document.getElementById("parked");
    const hasParked = snapshot.records.some(r => r.kind === "item" && r.data.title === "Parked" && r.data.member_ids?.length);
    if (parked && !hasParked) parked.hidden = true;
    if (this.topicFocusId && els.has(this.topicFocusId)) {
      const box = this.#displayed(els.get(this.topicFocusId)), r = this.root.getBoundingClientRect();
      const z = Math.min(1, (r.width-120)/box.w, (r.height-120)/box.h);
      this.view = {x:(r.width-box.w*z)/2-box.x*z, y:72-box.y*z, z, touched:true};
      this.topicFocusId = null;
      this.#apply();
    } else if (!this.view.touched) this.fit(); else this.#apply();
    if (keepFocus) {
      const target = this.world.querySelector(`[data-focus-key="${keepFocus}"]`);
      target?.focus({preventScroll:true});
      if (caret && target?.setSelectionRange) target.setSelectionRange(...caret);
    }
    this.lastEls = els;
    this.hooks.onSelection?.([...this.selected]);
    for (const fn of this.decorators) {
      try { fn(this.world, model); } catch (error) { console.error("A board decoration failed:", error); }
    }
    this.root.dispatchEvent(new CustomEvent("jv:board-rendered", {detail:{model}}));
    return model;
  }

  /** What changed since the last render, drawn as motion (DESIGN.md 1.1):
   * new proposals land, staggered in wall reading order; a proposal that
   * became an item settles straight, fills and swells by 3%; a proposal that
   * left without becoming one fades and shrinks out. Only with the motion
   * helper and never on the first render, so opening a board does not
   * replay its history. */
  #motion(model, els) {
    const looks = new Map(model.notes.map(n => [n.id,
      n.kind === "item" ? "item" : machineMade(n) ? "proposed" : "typed"]));
    const before = this.seen, previousEls = this.lastEls;
    this.seen = looks;
    this.lastEls = els;
    const settle = this.settle;
    if (!before || !settle) return;

    const acceptedFrom = new Map();
    for (const n of model.notes) {
      const from = n.kind === "item" ? n.data.proposal_id : null;
      if (from && !before.has(n.id) && ["proposed", "typed"].includes(before.get(from))) acceptedFrom.set(from, n.id);
    }

    const rank = new Map(model.notes.map((n, i) => [n.id, i]));
    const landing = model.notes.filter(n => n.kind === "proposal" && !before.has(n.id)).sort(readingOrder(rank));
    landing.forEach((n, i) => {
      const el = els.get(n.id);
      el.style.setProperty("--i", String(i));
      settle(el, "note-landing").then(() => el.style.removeProperty("--i"));
    });

    for (const [from, id] of acceptedFrom) {
      const el = els.get(id);
      const was = before.get(from);
      // Start from exactly what was on screen: the proposal's angle and fill.
      el.style.setProperty("--rot", `${was === "proposed" ? noteRotation(from) : 0}deg`);
      el.style.setProperty("--note-accent-soft", was === "proposed" ? "var(--note-proposed-fill)" : "var(--surface)");
      settle(el, "note-accepting").then(() => {
        el.style.removeProperty("--rot");
        el.style.removeProperty("--note-accent-soft");
      });
    }

    for (const [id, look] of before) {
      if (look === "item" || looks.has(id) || acceptedFrom.has(id)) continue;
      const ghost = previousEls.get(id);
      if (!ghost) continue;
      // The rejected note's last drawing, kept just long enough to leave.
      // No id, so nothing selects it; no presses, so nothing acts on it.
      ghost.removeAttribute("data-id");
      ghost.classList.remove("item-selected");
      ghost.classList.add("note-ghost");
      ghost.setAttribute("aria-hidden", "true");
      this.world.append(ghost);
      settle(ghost, "note-rejecting", { keep: true }).then(() => ghost.remove());
    }
  }

  #note(snapshot, r, model, palette) {
    const el = document.createElement("article");
    const provisional = r.kind === "proposal" && machineMade(r);
    el.className = "note item " + widthStep(r.data.summary_detail || r.data.text) + " " +
      (r.kind === "item" ? "item-accepted" : provisional ? "item-provisional" : "item-pending") +
      ` note-${this.topicTones?.get(r.id) || noteAccent(r, palette)}` + (isCorrected(r) ? " note-corrected" : "") + (this.readonly ? " readonly" : "") +
      // The post-it look (css/canvas.css). Polls and command documents are
      // .note too and stay cards, so the look needs its own class.
      " note-sticky";
    if (this.selected.has(r.id)) el.classList.add("item-selected");
    el.dataset.id = r.id;
    el.dataset.kind = r.kind;
    el.dataset.revision = String(r.position?.revision ?? 0);
    el.setAttribute("aria-label", r.data.text);
    // The angle is a custom property, not transform: the board writes
    // transform for the details offset, and the CSS clamps the angle.
    if (provisional) el.style.setProperty("--rot", `${noteRotation(r.id)}deg`);

    if (r.data.automatic && machineMade(r)) {
      const badge = document.createElement("span");
      badge.className = "badge st-provisional";
      badge.textContent = r.data.summary_topic_id ? (r.data.synthetic ? "Scripted summary" : "AI summary") : r.data.synthetic ? "Stand-in reading" : "AI reading";
      el.append(badge);
    } else if (provisional) {
      const badge = document.createElement("span");
      badge.className = "badge st-provisional";
      badge.innerHTML = '<i class="glyph glyph-provisional" aria-hidden="true"></i>Proposed';
      el.append(badge);
    } else if (r.kind === "proposal") {
      const badge = document.createElement("span");
      badge.className = "badge st-off";
      badge.textContent = "Not yet reviewed";
      el.append(badge);
    }
    const head = document.createElement("span");
    head.className = "note-head";
    if (r.data.colour?.hex) {
      // The measured paper colour itself, beside the label: the fill is the
      // nearest accent, so the sample keeps the exact evidence in view.
      const sw = document.createElement("i");
      sw.className = "swatch";
      sw.style.background = r.data.colour.hex;
      sw.setAttribute("aria-hidden", "true");
      head.append(sw);
    }
    const kind = document.createElement("span");
    kind.className = "kind";
    // The group's name is on its rectangle; repeating it in every note is noise.
    kind.textContent = noteKind(r);
    head.append(kind);
    const text = document.createElement("span");
    text.className = "text";
    text.textContent = r.data.text;
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = r.kind === "item" ? acceptedStamp(snapshot, r) : noteMeta(snapshot, r);
    el.append(text);
    const dated = this.#dateChip(snapshot, r);
    if (dated) el.append(dated);
    // The provenance (kind line and stamp) is printed on a chip at the
    // note's bottom edge, so the note's words and the machine's label read
    // as two things. It comes last, after the buttons and the details, so
    // it stays at the edge when details open and the tab order follows
    // what is seen.
    const chip = document.createElement("footer");
    chip.className = "note-chip";
    chip.append(head, meta);

    const actions = document.createElement("div");
    actions.className = "note-actions";
    const open = this.expanded.has(r.id);
    const detailId = `detail-${r.id}`;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "btn btn-quiet btn-sm";
    toggle.textContent = open ? "Hide details" : "Show details";
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-controls", detailId);
    toggle.dataset.focusKey = `toggle-${r.id}`;
    toggle.addEventListener("click", () => {
      this.toggle(r.id);
      if (this.isTopicLayout() && this.expanded.has(r.id)) this.topicFocusId = r.id;
      this.render(this.snapshot);
    });
    actions.append(toggle);
    if (r.kind === "proposal") {
      // Collapsed notes offer Review, not Accept: expandable-notes.md. Review
      // opens the whole proposal where accepting is possible.
      const review = document.createElement("button");
      review.type = "button";
      review.className = "btn btn-secondary btn-sm";
      review.textContent = "Review";
      review.dataset.focusKey = `review-${r.id}`;
      review.addEventListener("click", () => this.hooks.review(r.id));
      actions.append(review);
    }
    el.append(actions);

    const details = document.createElement("div");
    details.className = "details";
    details.id = detailId;
    details.hidden = !open;
    if (open) details.append(this.#details(snapshot, r, model));
    el.append(details, chip);

    if (this.isTopicLayout()) {
      toggle.setAttribute("aria-label", open ? "Hide details" : "Show details");
      toggle.className = "topic-note-title";
      toggle.textContent = r.data.text;
      text.replaceWith(toggle);
      if (!actions.children.length) actions.remove();
    }

    this.#drag(el, r);
    return el;
  }

  /** Provenance only. There is no summary field yet, so the note already
   * shows its full text; details never invent context it does not have. */
  #details(snapshot, r, model) {
    const dl = document.createElement("dl");
    dl.className = "facts";
    const add = (term, value) => {
      const dt = document.createElement("dt"); dt.textContent = term;
      const dd = document.createElement("dd");
      if (value instanceof Node) dd.append(value); else dd.textContent = value;
      dl.append(dt, dd);
    };
    if (r.data.summary_batch_id) {
      add("Created by", r.data.provider || "Summary-to-sticky bridge");
    } else if (machineMade(r)) {
      add("Read by", `${readerName(r.data)} (${r.data.model ?? "unknown model"})` +
        (r.data.synthetic ? ". Stand-in reading: no handwriting recognition ran" : ""));
    } else if (r.data.region_id) {
      add("Read by", "A person, from the photograph");
    } else {
      add("Written by", memberName(snapshot, r.data.author_id ?? r.data.last_editor));
    }
    if (r.data.summary_detail) {
      add("Type", r.data.summary_category ?? "Insight");
    }
    if (r.data.reading_status === "human_transcribed" && machineMade(r)) add("Text", "Retyped by a person");
    if ("confidence" in r.data) {
      add("Confidence", r.data.confidence == null ? "Not measured" : `${Math.round(r.data.confidence * 100)}% on ${r.data.model}'s own scale`);
    }
    if ("colour" in r.data) {
      if (r.data.colour == null) add("Paper colour", "Not measured");
      else {
        const span = document.createElement("span");
        span.className = "swatch-line";
        const sw = document.createElement("i");
        sw.className = "swatch";
        sw.style.background = r.data.colour.hex;
        span.append(sw, document.createTextNode(
          `${r.data.colour.hex}, ${r.data.colour.source === "pixel_measured" ? "measured from the photo" : "named by the model"}`));
        add("Paper colour", span);
      }
    }
    if (r.data.automatic) add("Added", "Automatically, without human acceptance");
    else if (r.kind === "item") add("Accepted by", memberName(snapshot, r.data.accepted_by));
    const group = model.groupOf.get(r.id);
    if (group) add("Group", group.data.text);
    const topic = this.topicAssociations?.get(r.id);
    if (topic) add("Layout topic", `${topic.label} (${topic.basis === "summary" ? "from summary" : "suggested grouping"})`);
    add("Position", !r.position ? "Not placed yet" : r.position.hand_placed ? "Placed by a person" : "Placed by the layout");

    const wrap = document.createElement("div");
    wrap.append(dl);
    if (r.data.summary_detail) {
      const summary = document.createElement("p"); summary.className = "t-body summary-note-detail";
      summary.textContent = r.data.summary_detail; wrap.append(summary);
    }
    const mine = snapshot.members?.find(m => m.id === snapshot.actor_id);
    if (r.data.automatic && r.kind === "item" && mine?.role === "facilitator" && !this.readonly) {
      this.noteDrafts ??= new Map();
      const editor = document.createElement("textarea");
      editor.value = this.noteDrafts.get(r.id) ?? r.data.text;
      editor.setAttribute("aria-label", "Note text"); editor.dataset.focusKey = `note-edit-${r.id}`;
      editor.addEventListener("input", () => this.noteDrafts.set(r.id, editor.value));
      const save = document.createElement("button"); save.type = "button"; save.className = "btn btn-secondary btn-sm";
      save.textContent = "Save note";
      save.addEventListener("click", async () => {
        try { await this.hooks.send("item.edit", { item_id:r.id, expected_revision:r.revision,
          text:editor.value, refs:r.data.refs }); this.noteDrafts.delete(r.id); }
        catch { /* Shared send reports errors. */ }
      });
      wrap.append(editor, save);
    }
    const calendar = this.#calendarLink(snapshot, r);
    if (calendar) wrap.append(calendar);
    const source = r.data.refs?.[0];
    if (r.data.region_id && source) {
      const figure = document.createElement("figure");
      figure.className = "crop";
      const caption = document.createElement("figcaption");
      caption.className = "t-caption";
      caption.textContent = "The part of the photograph this came from";
      const cached = this.cropUrls.get(r.id);
      if (cached) {
        const img = document.createElement("img"); img.src = cached; img.alt = "Crop of the photographed note";
        const size = this.cropSizes.get(r.id);
        if (size) { img.width = size.w; img.height = size.h; }
        else img.addEventListener("load", () => {
          this.cropSizes.set(r.id, {w:img.naturalWidth, h:img.naturalHeight});
          if (this.isTopicLayout() && this.expanded.has(r.id)) {
            this.topicFocusId = r.id; this.render(this.snapshot);
          }
        }, {once:true});
        figure.append(img, caption);
      } else {
        caption.textContent = "Loading the photograph crop…";
        figure.append(caption);
        this.hooks.crop(source.id, source.revision, r.data.region_id).then(url => {
          if (!this.expanded.has(r.id)) { this.hooks.revoke(url); return; }
          this.cropUrls.set(r.id, url);
          this.render(this.snapshot);
        }).catch(() => {
          // Crops are for the uploader and facilitators only. Say so rather
          // than leave a loading line or a broken image.
          caption.textContent = "The photograph is not available to you: only its uploader and facilitators can see it.";
        });
      }
      wrap.append(figure);
    }
    return wrap;
  }

  /** The note's date, from the calendar event made from it (chips.mjs), or
   * null. Compared in the session's zone, so every screen agrees. */
  #dateChip(snapshot, r) {
    const event = noteEvents(snapshot, r.id)[0]?.record;
    const chip = event && dateChip(event.data, snapshot.session?.timezone);
    if (!chip) return null;
    const row = document.createElement("span");
    row.className = "note-dates";
    row.append(dateChipElement(chip));
    return row;
  }

  /** Add to calendar, in a note's details. It writes a calendar event through
   * calendar.entry.edit in the session's collecting calendar, with a link back
   * to the note; changing the date or removing the event uses the same
   * operation. With no collecting calendar it says so and offers nothing it
   * cannot do: making a calendar is the planning command's job. */
  #calendarLink(snapshot, r) {
    if (r.kind !== "item") return null;
    const mine = snapshot.members?.find(m => m.id === snapshot.actor_id);
    const canEdit = ["facilitator", "participant"].includes(mine?.role) && snapshot.session?.state === "active";
    const linked = noteEvents(snapshot, r.id)[0];
    const target = linked?.calendar ?? collectingCalendar(snapshot);
    const editable = canEdit && target && (linked ? ["collecting", "reviewing"] : ["collecting"]).includes(target.data.state);
    if (!linked && !canEdit) return null;
    const box = document.createElement("section");
    box.className = "note-calendar";
    box.setAttribute("aria-label", "Calendar");
    const line = (cls, words) => { const p = document.createElement("p"); p.className = cls; p.textContent = words; return p; };
    if (linked) {
      const chip = dateChip(linked.record.data, snapshot.session?.timezone);
      const said = line("note-calendar-state", chip ? "In the calendar: " : "In the calendar, without a date");
      if (chip) said.append(dateChipElement(chip));
      box.append(said);
    }
    if (!editable) {
      if (!linked) {
        box.append(line("note-calendar-state", "No calendar is collecting. Start one with the planning command, such as “make a calendar”, and this note can be added to it."));
        const none = document.createElement("button");
        none.type = "button"; none.className = "btn btn-secondary btn-sm"; none.disabled = true;
        none.textContent = "Add to calendar";
        box.append(none);
      }
      return box;
    }
    this.calendarDrafts ??= new Map();
    const event = linked?.record;
    const draft = this.calendarDrafts.get(r.id) ?? { date: event?.data.date ?? "", time: event?.data.time ?? "" };
    this.calendarDrafts.set(r.id, draft);
    const field = (name, label) => {
      const wrap = document.createElement("label");
      wrap.className = "note-calendar-field";
      const input = document.createElement("input");
      input.type = name; input.value = draft[name];
      input.dataset.focusKey = `note-calendar-${name}-${r.id}`;
      input.addEventListener("input", () => { draft[name] = input.value; });
      wrap.append(document.createTextNode(label), input);
      return wrap;
    };
    const send = async (payload, button) => {
      button.disabled = true;
      try {
        await this.hooks.send("calendar.entry.edit", { document_id: target.id, expected_revision: target.revision, ...payload });
        this.calendarDrafts.delete(r.id);
      } catch { /* Shared send reports errors. */ }
      finally { if (button.isConnected) button.disabled = false; }
    };
    const action = (label, run) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "btn btn-secondary btn-sm"; b.textContent = label;
      b.dataset.focusKey = `note-calendar-${label}-${r.id}`;
      b.addEventListener("click", () => run(b));
      return b;
    };
    const fields = document.createElement("div");
    fields.className = "note-calendar-fields";
    fields.append(field("date", "Date"), field("time", "Time, optional"));
    box.append(fields);
    const actions = document.createElement("div");
    actions.className = "note-actions";
    if (!event) {
      actions.append(action("Add to calendar", b => {
        if (!draft.date) { this.hooks.attention?.("Choose a date for the calendar first.", "note"); return; }
        return send({ entry_id: "", task_id: "", note_id: r.id, removed: false,
          value: { text: eventText(r.data.text), date: draft.date, time: draft.time, done: false, date_changed: true } }, b);
      }));
    } else {
      const value = { text: event.data.text, date: event.data.date, time: event.data.time, done: event.data.done };
      actions.append(action("Save date", b => send({ entry_id: event.id, task_id: "", expected_entry_revision: event.revision,
        removed: false, value: { ...value, date: draft.date, time: draft.time, date_changed: true } }, b)),
      action("Remove from calendar", b => send({ entry_id: event.id, task_id: "", expected_entry_revision: event.revision,
        removed: true, value: { ...value, date_changed: false } }, b)));
    }
    box.append(actions);
    return box;
  }

  toggle(id, open = !this.expanded.has(id)) {
    if (open) this.expanded.add(id);
    else {
      this.expanded.delete(id);
      const url = this.cropUrls.get(id);
      if (url) { this.hooks.revoke(url); this.cropUrls.delete(id); }
    }
  }

  /** Local display offsets for open notes, from saved geometry every time. */
  #displace(els) {
    const open = [...els.entries()].filter(([id]) => this.expanded.has(id)).map(([, el]) => {
      const d = el.querySelector(".details");
      return { el, x: parseFloat(el.style.left), y: parseFloat(el.style.top), w: el.offsetWidth, grow: d.offsetHeight + DETAIL_GAP };
    });
    for (const el of els.values()) {
      const x = parseFloat(el.style.left), y = parseFloat(el.style.top), w = el.offsetWidth;
      let offset = 0;
      for (const o of open) {
        if (o.el !== el && y > o.y && x < o.x + o.w && x + w > o.x) offset += o.grow;
      }
      el.dataset.offset = String(offset);
      el.style.transform = offset ? `translateY(${offset}px)` : "";
    }
  }

  /** A group: the soft rectangle behind its members and its label inside the
   * top left. Returned rather than put in, so it can be layered under the
   * drawings. */
  #hull(cluster, els, provisional) {
    const members = cluster.data.refs.map(ref => els.get(ref.id)).filter(Boolean);
    if (!members.length) return null;
    const box = hullBox(members.map(el => this.#displayed(el)));
    const hull = document.createElement("section");
    hull.className = "hull " + (provisional ? "hull-provisional" : "hull-accepted");
    hull.dataset.id = cluster.id;
    hull.setAttribute("aria-label", `${provisional ? "Proposed group" : "Group"}: ${cluster.data.text}`);
    Object.assign(hull.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px`, height: `${box.h}px` });
    const label = document.createElement("span");
    label.className = "hull-label";
    if (provisional) {
      label.innerHTML = '<i class="glyph glyph-provisional" aria-hidden="true"></i>';
      label.append(document.createTextNode(`Proposed group · ${cluster.data.text}`));
      const review = document.createElement("button");
      review.type = "button"; review.className = "btn btn-quiet btn-sm"; review.textContent = "Review";
      review.addEventListener("click", () => this.hooks.review(cluster.id));
      label.append(review);
    } else {
      label.textContent = `Group · ${cluster.data.text}`;
    }
    hull.append(label);
    return { id: cluster.id, el: hull, box };
  }

  // -------------------------------------------------------- canvas objects

  /** Sections, shapes, text, connectors and pen strokes. Drawn after the notes
   * are placed and pushed, because a connector ends at a note's displayed box;
   * put in before the notes, so they are drawn under them. Bottom to top:
   * sections, groups, shapes and text, the marks layer, then the labels that
   * float on the marks. */
  #objects(model, els, hulls, laneSlot) {
    this.linkBounds = [];
    const boxes = new Map();
    for (const [id, el] of els) boxes.set(id, { ...this.#displayed(el), outline: "rect" });
    for (const h of hulls) boxes.set(h.id, h.box);
    this.hitBoxes = [];

    const sections = [], shapes = [], floats = [];
    // One layer for every connector and stroke. It takes no pointer events
    // (see canvas.css), so it can never swallow a press meant for a note or a
    // pan; only the eraser turns its hit paths on.
    const links = svg("svg", { class: "links", width: 1, height: 1, "aria-hidden": "true" });
    const look = obj => obj.proposed ? "cobj-proposed" : `tone-${toneOf(obj.fields)}`;

    for (const obj of model.objects) {
      if (obj.kind === "arrow") continue;
      if (obj.kind === "stroke") {
        let origin = obj.record.position;
        if (!origin) {
          const own = strokeBounds(obj.fields.points, { x: 0, y: 0 });
          if (!own) continue;
          const slot = laneSlot(own.h);
          origin = { x: slot.x - own.x, y: slot.y - own.y };
        }
        const d = strokePath(obj.fields.points, origin);
        if (!d) continue;
        const bounds = strokeBounds(obj.fields.points, origin);
        const weight = ["fine", "regular", "bold"].includes(obj.fields.weight) ? obj.fields.weight : "regular";
        const g = svg("g", { class: "mark" + (obj.proposed ? "" : " erasable"), ...(obj.proposed ? {} : { "data-hit": obj.id }) });
        g.append(svg("path", { d, class: `pen weight-${weight} ${look(obj)}`, "data-id": obj.id }));
        if (!obj.proposed) g.append(svg("path", { d, class: "stroke-hit" }));
        links.append(g);
        boxes.set(obj.id, bounds);
        this.linkBounds.push({ ...bounds, id: obj.id });
        if (obj.proposed) floats.push(this.#float(bounds.x, bounds.y, this.#tag(obj, "Proposed"), "above"));
        continue;
      }
      let position = obj.record.position;
      if (!position) position = laneSlot(objectBox(obj, { x: 0, y: 0 }).h);
      const box = objectBox(obj, position);
      if (!box) continue;
      const el = document.createElement("div");
      el.className = `cobj cobj-${obj.kind} ${look(obj)}`;
      el.dataset.id = obj.id;
      el.dataset.kind = obj.kind;
      Object.assign(el.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px`, height: `${box.h}px` });
      boxes.set(obj.id, box);

      if (obj.kind === "section") {
        el.setAttribute("role", "group");
        const title = obj.fields.title?.trim() || "Untitled section";
        el.setAttribute("aria-label", `Section: ${title}`);
        const head = obj.proposed ? this.#tag(obj, `Proposed section · ${title}`) : document.createElement("span");
        head.classList.add("cobj-title");
        if (!obj.proposed) head.textContent = `Section · ${title}`;
        el.append(head);
        sections.push(el);
        continue;
      }
      this.hitBoxes.push({ id: obj.id, box });
      if (obj.kind === "shape") {
        const kind = ["rect", "ellipse", "diamond", "line"].includes(obj.fields.shape) ? obj.fields.shape : "rect";
        el.classList.add(`shape-${kind}`);
        el.setAttribute("role", "img");
        el.setAttribute("aria-label", (obj.proposed ? "Proposed " : "") + `${kind === "rect" ? "rectangle" : kind}` +
          (obj.fields.text?.trim() ? `: ${obj.fields.text}` : ""));
        el.append(this.#outline(kind, box, obj.proposed));
        if (obj.fields.text?.trim()) {
          const text = document.createElement("span");
          text.className = "cobj-label";
          text.textContent = obj.fields.text;
          el.append(text);
        }
      } else {
        const size = ["body", "title", "heading"].includes(obj.fields.size) ? obj.fields.size : "body";
        const text = document.createElement("span");
        text.className = `cobj-words t-${size}`;
        text.textContent = obj.fields.text ?? "";
        el.append(text);
      }
      if (obj.proposed) el.append(this.#tag(obj, "Proposed"));
      shapes.push(el);
    }

    aliasAccepted(boxes, this.snapshot?.records);
    this.boxes = boxes;
    for (const obj of model.objects) {
      if (obj.kind !== "arrow") continue;
      const ends = arrowEnds(obj.fields, boxes);
      const curve = ends && connectorGeometry(ends.from, ends.to);
      if (!curve) continue;
      const directed = this.directed.has(obj.id);
      const g = svg("g", { class: `arrow connector ${look(obj)}` + (directed ? " connector-directed" : "") + (obj.proposed ? "" : " erasable"),
        "data-id": obj.id, ...(obj.proposed ? {} : { "data-hit": obj.id }) });
      g.append(svg("path", { class: "arrow-line", d: curve.d }));
      if (directed) g.append(svg("path", { class: "arrow-head connector-head", d: connectorHead(curve) }));
      if (!obj.proposed) g.append(svg("path", { class: "stroke-hit", d: curve.d }));
      links.append(g);
      // The curve lies inside the box of its ends and control points.
      const pts = [curve.start, curve.c1, curve.c2, curve.end];
      const x = Math.min(...pts.map(p => p.x)), y = Math.min(...pts.map(p => p.y));
      this.linkBounds.push({ id: obj.id, x, y, w: Math.max(...pts.map(p => p.x)) - x, h: Math.max(...pts.map(p => p.y)) - y });
      const label = obj.fields.label?.trim();
      if (obj.proposed) floats.push(this.#float(curve.mid.x, curve.mid.y, this.#tag(obj, "Proposed"), "over"));
      if (label) {
        const words = document.createElement("span");
        words.className = "arrow-label connector-label";
        words.textContent = label;
        floats.push(this.#float(curve.mid.x, curve.mid.y, words, "middle"));
      }
    }
    this.world.prepend(...sections, ...hulls.map(h => h.el), ...shapes, links, ...floats);
  }

  /** The drawn outline of a shape, sized to its box in its own pixels. A
   * proposed outline is inset by half its 1px line so the dash is not cut. */
  #outline(kind, { w, h }, proposed) {
    const i = proposed ? 0.5 : 0;
    const s = svg("svg", { class: "cobj-outline", width: w, height: h, viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" });
    const body = kind === "ellipse" ? svg("ellipse", { cx: w / 2, cy: h / 2, rx: w / 2 - i, ry: h / 2 - i })
      : kind === "diamond" ? svg("polygon", { points: `${w / 2},${i} ${w - i},${h / 2} ${w / 2},${h - i} ${i},${h / 2}` })
      // A line runs corner to corner of its box: the box is the line's bounds.
      : kind === "line" ? svg("line", { x1: 1, y1: 1, x2: w - 1, y2: h - 1 })
      : svg("rect", { x: i, y: i, width: w - 2 * i, height: h - 2 * i });
    body.setAttribute("class", kind === "line" ? "rule" : "body");
    s.append(body);
    return s;
  }

  /** "Proposed" with the dashed ring, and Review, as on a proposed group. */
  #tag(obj, words) {
    const tag = document.createElement("span");
    tag.className = "cobj-tag st-provisional";
    tag.innerHTML = '<i class="glyph glyph-provisional" aria-hidden="true"></i>';
    tag.append(document.createTextNode(words));
    const review = document.createElement("button");
    review.type = "button"; review.className = "btn btn-quiet btn-sm"; review.textContent = "Review";
    review.addEventListener("click", () => this.hooks.review(obj.id));
    tag.append(review);
    return tag;
  }

  /** A label for something on the SVG layer, placed in the world. */
  #float(x, y, content, where) {
    const el = document.createElement("div");
    el.className = `cobj-float cobj-float-${where}`;
    el.style.left = `${x}px`; el.style.top = `${y}px`;
    el.append(content);
    return el;
  }

  // -------------------------------------------------------------------- drag

  /** Where a person dropped this note, while the server's snapshot still
   * says the old place. The reply to item.place is not merged into the
   * snapshot, so for up to a poll the next render would put the note back
   * where it was and then jump it forward when the poll lands. The server's
   * answer wins as soon as it carries a newer position revision. */
  #dropped(note) {
    const kept = this.placed.get(note.id);
    if (!kept) return null;
    if ((note.position?.revision ?? 0) > kept.revision) { this.placed.delete(note.id); return null; }
    return kept;
  }

  #drag(el, r) {
    if (this.readonly || this.isTopicLayout()) {
      // Read only on touch: a tap selects, nothing moves.
      el.addEventListener("click", event => {
        if (event.target.closest("button, a, img, input, textarea, select, summary, label")) return;
        if (!["poll", "command_document"].includes(r.kind)) this.select(r.id, event.shiftKey || event.metaKey || event.ctrlKey);
      });
      return;
    }
    let start = null;
    el.addEventListener("pointerdown", event => {
      if (event.target.closest("button, a, img, input, textarea, select, summary, label")) return;
      event.stopPropagation();
      // A press is the start of a move, not of a text selection: without
      // this the browser selects the note's words as the pointer travels.
      if (event.button === 0) event.preventDefault();
      // The connector takes a press on a note as one of its ends.
      if (this.tool !== "select" && event.button === 0 && this.#toolPress(event, { kind: "note", id: r.id })) return;
      if (this.expanded.has(r.id) || Number(el.dataset.offset)) {
        // An open or pushed note is drawn away from where it is saved. Moving
        // it now would save a display offset as if a person put it there.
        start = { blocked: true, x: event.clientX, y: event.clientY };
        return;
      }
      start = { x: event.clientX, y: event.clientY, left: parseFloat(el.style.left), top: parseFloat(el.style.top), moved: false };
      el.setPointerCapture(event.pointerId);
      this.busy = true;
    });
    el.addEventListener("pointermove", event => {
      if (!start || start.blocked) return;
      const dx = (event.clientX - start.x) / this.view.z, dy = (event.clientY - start.y) / this.view.z;
      if (Math.abs(dx) + Math.abs(dy) > 3) start.moved = true;
      if (!start.moved) return;
      el.style.left = `${start.left + dx}px`;
      el.style.top = `${start.top + dy}px`;
      el.classList.add("dragging");
    });
    el.addEventListener("pointerup", async event => {
      if (!start) return;
      const from = start; start = null;
      el.classList.remove("dragging");
      if (from.blocked) {
        const moved = Math.abs(event.clientX - from.x) + Math.abs(event.clientY - from.y) > 3;
        if (moved) this.hooks.attention("Hide the open details before moving notes. Details only change your screen, so a move made while they are open would save the wrong place.", "note");
        else if (!["poll", "command_document"].includes(r.kind)) this.select(r.id, event.shiftKey || event.metaKey || event.ctrlKey);
        return;
      }
      if (!from.moved) { this.busy = false; if (!["poll", "command_document"].includes(r.kind)) this.select(r.id, event.shiftKey || event.metaKey || event.ctrlKey); return; }
      const x = Math.round(parseFloat(el.style.left)), y = Math.round(parseFloat(el.style.top));
      const join = ["poll", "command_document"].includes(r.kind) ? null : this.#hullUnder(el, r);
      const revision = Number(el.dataset.revision);
      // The note stays where it was dropped from this moment: the server is
      // asked, and until it answers (or refuses) nothing redraws it elsewhere.
      this.placed.set(r.id, { x, y, revision });
      try {
        // No review. Moving is not agreeing with the content.
        await this.hooks.send("item.place", { placements: [{ id: r.id, x, y,
          expected_position_revision: revision }] });
        if (r.kind === "item") await this.#membership(r, join);
      } catch {
        // Put it back: a refused move must not look like it worked.
        this.placed.delete(r.id);
        el.style.left = `${from.left}px`;
        el.style.top = `${from.top}px`;
      } finally {
        this.#settle();
      }
    });
  }

  /** The accepted group whose rectangle (drawn without this note) holds the
   * note's centre, or null. canvas-layout.md: the centre decides. */
  #hullUnder(el, r) {
    const box = this.#displayed(el);
    const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
    const model = boardModel(this.snapshot);
    for (const c of model.clusters) {
      const others = c.data.refs.filter(ref => ref.id !== r.id)
        .map(ref => this.world.querySelector(`.note[data-id="${ref.id}"]`)).filter(Boolean).map(m => this.#displayed(m));
      const h = hullBox(others);
      if (h && cx >= h.x && cx <= h.x + h.w && cy >= h.y && cy <= h.y + h.h) return c;
    }
    return null;
  }

  async #membership(r, target) {
    const current = boardModel(this.snapshot).groupOf.get(r.id) ?? null;
    if (current?.id === target?.id) return;
    if (current) {
      await this.hooks.send("cluster.membership", { cluster_id: current.id, expected_revision: current.revision, remove: [r.id] });
    }
    if (target) {
      const fresh = this.snapshot.records.find(x => x.id === target.id) ?? target;
      await this.hooks.send("cluster.membership", { cluster_id: fresh.id, expected_revision: fresh.revision, add: [r.id] });
    }
  }
}
