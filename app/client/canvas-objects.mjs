/**
 * The canvas objects that are not notes: shapes, text, arrows, sections and
 * pen strokes (docs/specs/2026-10-18-canvas-object-model.md).
 *
 * Everything here is pure: no DOM, no network. The board draws from these
 * functions and the list view labels from them, so the two views cannot
 * disagree about what an object is or where an arrow goes, and the geometry
 * can be tested in Node without a browser.
 *
 * Two record shapes carry the same object, and `canvasObject` folds them into
 * one:
 *
 *   An item (`item_kind` shape, text, arrow, section or stroke) keeps its
 *   fields on `data`. It was made by hand or accepted, so it is drawn with the
 *   accepted look.
 *
 *   A proposal (`proposal_kind: "canvas"`) keeps them on `data.canvas_data`,
 *   with the kind in `data.canvas_kind`. A model made it and nobody accepted
 *   it, so it is drawn proposed.
 */

export const CANVAS_KINDS = ["shape", "text", "arrow", "section", "stroke"];

/** The spec's closed set. Anything else draws as ink, the neutral tone, rather
 * than failing: a tone the client does not know must not hide the object. */
export const TONES = ["ink", "accent", "category-1", "category-2", "category-3"];

/** Sizes for an object the server sent without one, which should only happen
 * for a proposal whose position has no size yet. Each is a note width step, so
 * an unsized object lines up with the notes in the lane. */
export const DEFAULT_SIZE = {
  shape: { w: 160, h: 96 },
  text: { w: 224, h: 48 },
  section: { w: 336, h: 224 },
};

const OPEN = ["needs_review", "stale"];

/** One object from one record, or null if the record is not a drawable canvas
 * object (a note, a cluster, an undone item, a decided proposal). */
export function canvasObject(record) {
  const data = record?.data;
  if (!data) return null;
  if (record.kind === "item" && CANVAS_KINDS.includes(data.item_kind) && data.status === "accepted") {
    return { id: record.id, kind: data.item_kind, fields: data, proposed: false, record };
  }
  if (record.kind === "proposal" && data.proposal_kind === "canvas" && CANVAS_KINDS.includes(data.canvas_kind) &&
      OPEN.includes(data.status)) {
    return { id: record.id, kind: data.canvas_kind, fields: data.canvas_data ?? {}, proposed: true, record };
  }
  return null;
}

export function toneOf(fields) {
  return TONES.includes(fields?.tone) ? fields.tone : "ink";
}

const finite = n => typeof n === "number" && Number.isFinite(n);

/** The box a positioned object occupies, in world coordinates, with the outline
 * an arrow should stop at. Null for arrows, which have no box of their own. */
export function objectBox(obj, position) {
  if (!position || !finite(position.x) || !finite(position.y)) return null;
  if (obj.kind === "stroke") return strokeBounds(obj.fields.points, position);
  if (!DEFAULT_SIZE[obj.kind]) return null;
  const size = DEFAULT_SIZE[obj.kind];
  const w = finite(position.w) && position.w > 0 ? position.w : size.w;
  const h = finite(position.h) && position.h > 0 ? position.h : size.h;
  const outline = obj.kind === "shape" && ["ellipse", "diamond"].includes(obj.fields.shape) ? obj.fields.shape : "rect";
  return { x: position.x, y: position.y, w, h, outline };
}

// ----------------------------------------------------------------- arrows

/** Where a ray from the box's centre toward `toward` leaves the box's outline.
 * Rectangles, ellipses and diamonds each have an exact answer, so an arrow
 * ends on the shape's edge rather than on its bounding box. */
export function edgePoint(box, toward) {
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  const dx = toward.x - cx, dy = toward.y - cy;
  if (dx === 0 && dy === 0) return { x: cx, y: cy };
  const a = box.w / 2, b = box.h / 2;
  let t;
  if (box.outline === "ellipse") t = 1 / Math.sqrt((dx / a) ** 2 + (dy / b) ** 2);
  else if (box.outline === "diamond") t = 1 / (Math.abs(dx) / a + Math.abs(dy) / b);
  else t = Math.min(dx ? a / Math.abs(dx) : Infinity, dy ? b / Math.abs(dy) : Infinity);
  return { x: cx + dx * t, y: cy + dy * t };
}

const isBox = end => end && finite(end.w) && finite(end.h);
const centre = end => isBox(end) ? { x: end.x + end.w / 2, y: end.y + end.h / 2 } : { x: end.x, y: end.y };

/**
 * The visible segment of an arrow between two ends, each a box or a point.
 * Edge to edge, not centre to centre: an arrow drawn to a note's centre would
 * run under the note and its head would be hidden.
 *
 * Both ends lie on the line between the centres, and every outline here is
 * convex, so while the start comes before the end along that line the segment
 * is outside both boxes. When it does not (one box over the other's centre
 * line, a point inside the other box, two ends at one place) there is nothing
 * honest to draw and this is null. The list view still names the arrow, so it
 * is never lost. Boxes that merely overlap at a corner still get their arrow.
 */
export function arrowGeometry(from, to) {
  if (!from || !to) return null;
  const a = centre(from), b = centre(to);
  const start = isBox(from) ? edgePoint(from, b) : a;
  const end = isBox(to) ? edgePoint(to, a) : b;
  const dx = end.x - start.x, dy = end.y - start.y;
  if ((dx * (b.x - a.x) + dy * (b.y - a.y)) <= 0 || Math.hypot(dx, dy) < 1) return null;
  return { x1: start.x, y1: start.y, x2: end.x, y2: end.y };
}

/** An end is `{id}` (a record on the canvas) or `{x, y}` (a point). A record
 * that is not drawn has no box here, and the arrow is not drawn: an arrow
 * pointing at nothing would claim a connection the canvas no longer shows. */
/** Accepting a proposal makes a new item with a new id, and the item records
 * the proposal it came from (`data.proposal_id`). An arrow drawn to the
 * proposal keeps pointing at the same thing once it is accepted, so the
 * proposal's id is given the item's box when it has none of its own. */
export function aliasAccepted(boxes, records) {
  for (const r of records ?? []) {
    const from = r?.kind === "item" ? r.data?.proposal_id : null;
    if (from && !boxes.has(from) && boxes.has(r.id)) boxes.set(from, boxes.get(r.id));
  }
  return boxes;
}

export function resolveEnd(end, boxes) {
  if (end && typeof end.id === "string") return boxes.get(end.id) ?? null;
  if (end && finite(end.x) && finite(end.y)) return { x: end.x, y: end.y };
  return null;
}

/** Both ends of an arrow, or null if either is missing or it points from a
 * record to itself (the server refuses that; the client does not draw it). */
export function arrowEnds(fields, boxes) {
  if (fields?.from?.id && fields.from.id === fields?.to?.id) return null;
  const from = resolveEnd(fields?.from, boxes), to = resolveEnd(fields?.to, boxes);
  return from && to ? { from, to } : null;
}

/** An open chevron at the arrow's tip, as a path. Open rather than filled so a
 * proposed arrow's head is never a fill. */
export function arrowHead({ x1, y1, x2, y2 }, size = 10) {
  const angle = Math.atan2(y2 - y1, x2 - x1), spread = Math.PI / 7;
  const p = a => `${round(x2 - size * Math.cos(a))} ${round(y2 - size * Math.sin(a))}`;
  return `M ${p(angle - spread)} L ${round(x2)} ${round(y2)} L ${p(angle + spread)}`;
}

// ------------------------------------------------------------- connectors

const SIDE_NORMAL = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };

/** The middle of one side of a box, or the point itself for a point end. The
 * middle of each side of the bounding box lies on the rectangle, the ellipse
 * and the diamond alike, so one rule serves every outline. */
export function sidePoint(end, side) {
  if (!isBox(end)) return { x: end.x, y: end.y };
  const { x, y, w, h } = end;
  if (side === "left") return { x, y: y + h / 2 };
  if (side === "right") return { x: x + w, y: y + h / 2 };
  if (side === "top") return { x: x + w / 2, y };
  return { x: x + w / 2, y: y + h };
}

/**
 * Which sides a connector leaves and enters by: the pair that faces across the
 * wider gap between the two ends. Two notes side by side are joined right to
 * left; one above the other, bottom to top. A point end is a box of no size.
 */
export function nearestSides(from, to) {
  const box = end => isBox(end) ? end : { x: end.x, y: end.y, w: 0, h: 0 };
  const a = box(from), b = box(to);
  const gapX = Math.max(b.x - (a.x + a.w), a.x - (b.x + b.w));
  const gapY = Math.max(b.y - (a.y + a.h), a.y - (b.y + b.h));
  const ca = centre(a), cb = centre(b);
  if (gapX >= gapY) return cb.x >= ca.x ? ["right", "left"] : ["left", "right"];
  return cb.y >= ca.y ? ["bottom", "top"] : ["top", "bottom"];
}

/**
 * A connector between two ends: a cubic curve that leaves one end and enters
 * the other at the middle of their nearest sides, each control point pushed
 * straight out of its side, so the curve meets every edge at a right angle.
 * Null wherever a straight arrow would be null (one box over the other's
 * centre, two ends at one place), because a curve there would claim a
 * connection the canvas cannot show honestly.
 *
 * Returns the path, its two ends and control points, the sides used, and the
 * point halfway along the curve, where a label sits.
 */
export function connectorGeometry(from, to) {
  if (!arrowGeometry(from, to)) return null;
  const [s1, s2] = nearestSides(from, to);
  const start = sidePoint(from, s1), end = sidePoint(to, s2);
  const reach = Math.max(24, Math.min(160, Math.hypot(end.x - start.x, end.y - start.y) * 0.45));
  const push = (p, side) => ({ x: p.x + SIDE_NORMAL[side][0] * reach, y: p.y + SIDE_NORMAL[side][1] * reach });
  const c1 = push(start, s1), c2 = push(end, s2);
  const mid = { x: (start.x + 3 * c1.x + 3 * c2.x + end.x) / 8, y: (start.y + 3 * c1.y + 3 * c2.y + end.y) / 8 };
  const xy = p => `${round(p.x)} ${round(p.y)}`;
  return { start, c1, c2, end, sides: [s1, s2], mid, d: `M ${xy(start)} C ${xy(c1)} ${xy(c2)} ${xy(end)}` };
}

/** The open chevron at a directed connector's end, pointing along the curve's
 * last tangent (from the second control point to the end). */
export function connectorHead(geometry, size = 10) {
  const { c2, end } = geometry;
  return arrowHead({ x1: c2.x, y1: c2.y, x2: end.x, y2: end.y }, size);
}

// ---------------------------------------------------------------- colour

/** The five accents in the order the design names them. */
export const ACCENTS = ["yellow", "lilac", "mint", "periwinkle", "coral"];

/** `#rgb`, `#rrggbb` or `rgb(r, g, b)` as [r, g, b], or null. */
export function parseColour(value) {
  const s = String(value ?? "").trim();
  let m = s.match(/^#([0-9a-f]{3})$/i);
  if (m) return [...m[1]].map(c => parseInt(c + c, 16));
  m = s.match(/^#([0-9a-f]{6})$/i);
  if (m) return [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16));
  m = s.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i);
  if (m) return [m[1], m[2], m[3]].map(Number);
  return null;
}

/**
 * The accent a photographed note is drawn in: the one nearest its measured
 * paper colour, by plain distance in RGB. `palette` maps each accent name to
 * its colour (the board reads them from tokens.css at run time, so the
 * literals live in one file). Yellow when the colour cannot be read, because
 * a typed note is yellow and an unread colour is no evidence of another.
 */
export function nearestAccent(colour, palette) {
  const rgb = Array.isArray(colour) ? colour : parseColour(colour);
  if (!rgb || !palette) return "yellow";
  let best = "yellow", bestDistance = Infinity;
  for (const name of ACCENTS) {
    const p = Array.isArray(palette[name]) ? palette[name] : parseColour(palette[name]);
    if (!p) continue;
    const d = (rgb[0] - p[0]) ** 2 + (rgb[1] - p[1]) ** 2 + (rgb[2] - p[2]) ** 2;
    if (d < bestDistance) { best = name; bestDistance = d; }
  }
  return best;
}

// ---------------------------------------------------------------- strokes

const round = n => Math.round(n * 100) / 100;

function strokePoints(points, origin) {
  if (!Array.isArray(points)) return [];
  return points.filter(p => Array.isArray(p) && finite(p[0]) && finite(p[1]))
    .map(([x, y]) => [origin.x + x, origin.y + y]);
}

/**
 * A smooth path through a pen stroke's points, which are relative to the
 * stroke's position. Quadratic curves through the midpoints: each sampled
 * point is a control point, so the line passes near every sample without the
 * corners a polyline shows at a pen's sampling rate. Null with fewer than two
 * usable points, because one point is not a line.
 */
export function strokePath(points, origin = { x: 0, y: 0 }) {
  const p = strokePoints(points, origin);
  if (p.length < 2) return null;
  const xy = ([x, y]) => `${round(x)} ${round(y)}`;
  if (p.length === 2) return `M ${xy(p[0])} L ${xy(p[1])}`;
  let d = `M ${xy(p[0])}`;
  for (let i = 1; i < p.length - 1; i++) {
    const mid = [(p[i][0] + p[i + 1][0]) / 2, (p[i][1] + p[i + 1][1]) / 2];
    d += ` Q ${xy(p[i])} ${xy(mid)}`;
  }
  return `${d} L ${xy(p.at(-1))}`;
}

/** The world box around a stroke's points, so an arrow can end at a stroke and
 * the view can fit it. */
export function strokeBounds(points, origin) {
  const p = strokePoints(points, origin);
  if (!p.length) return null;
  const xs = p.map(q => q[0]), ys = p.map(q => q[1]);
  const x = Math.min(...xs), y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y, outline: "rect" };
}

// ----------------------------------------------------------------- labels

const SHAPE_WORDS = { rect: "Rectangle", ellipse: "Ellipse", diamond: "Diamond", line: "Line" };
const WEIGHT_WORDS = { fine: "Fine", regular: "Regular", bold: "Bold" };

export function shortText(text, max = 40) {
  const t = String(text ?? "").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1).trimEnd() + "…" : t;
}

/** How one object is named in a sentence, for an arrow's ends. A person's own
 * words are quoted, so they cannot be read as the client's. */
export function objectName(obj) {
  const f = obj.fields;
  const q = text => `“${shortText(text)}”`;
  if (obj.kind === "shape") return f.text?.trim() ? q(f.text) : `a ${SHAPE_WORDS[f.shape]?.toLowerCase() ?? "shape"}`;
  if (obj.kind === "text") return f.text?.trim() ? q(f.text) : "a text";
  if (obj.kind === "section") return f.title?.trim() ? `the section ${q(f.title)}` : "a section";
  if (obj.kind === "stroke") return "a pen stroke";
  return "an arrow";
}

/**
 * The list view's line for an object: "Shape · Ideas", "Arrow · from A to B",
 * "Section · Risks (3)". `nameOf(id)` names a record on the canvas, or returns
 * null when it is not there, so an arrow to something removed says so and a
 * section counts only the members still drawn.
 */
export function objectLabel(obj, nameOf = () => null) {
  const f = obj.fields;
  switch (obj.kind) {
    case "shape": return `Shape · ${f.text?.trim() ? shortText(f.text, 60) : SHAPE_WORDS[f.shape] ?? "Shape"}`;
    case "text": return `Text · ${shortText(f.text, 60) || "Empty"}`;
    case "section": {
      const present = (Array.isArray(f.member_ids) ? f.member_ids : []).filter(id => nameOf(id) != null).length;
      return `Section · ${f.title?.trim() ? shortText(f.title, 60) : "Untitled"} (${present})`;
    }
    case "stroke": return `Pen stroke · ${WEIGHT_WORDS[f.weight] ?? "Regular"}`;
    case "arrow": {
      const end = e => e?.id ? (nameOf(e.id) ?? "something no longer on the canvas") : "a point";
      const label = f.label?.trim() ? `${shortText(f.label, 40)} · ` : "";
      return `Arrow · ${label}from ${end(f.from)} to ${end(f.to)}`;
    }
    default: return obj.kind;
  }
}
