/**
 * The drawing tool: freehand ink, and the eraser (DESIGN.md 1.2).
 *
 * Draw: with the pen active, a drag that starts on empty canvas draws one
 * stroke in the human mark (ink at 85%, one weight, no pressure), smoothed
 * into quadratic curves through the midpoints of the samples. While it is
 * drawn it is an SVG path on the board's draft layer, under the notes, where
 * the saved stroke will be. On release it is simplified to at most 256 points
 * (the server's limit), made relative to its first point, and saved through
 * `canvas.create` as a `stroke`: a person's stroke is arranging, accepted at
 * once, like a move. The board then draws it from the snapshot like any
 * stroke; until then the draft stays, so the line never blinks out.
 *
 * A drag that starts on a note still moves the note, and a wheel or a
 * middle-button drag still pans, so the pen never traps anyone.
 *
 * Erase: with the eraser active, strokes and connectors take the pointer.
 * Hovering one dims it; a click removes it through `canvas.remove`, which
 * marks it undone, so the record keeps it.
 *
 * The pure parts (simplify, relativePoints, smoothPath, strokeRecord) are
 * exported for tests/draw-unit.mjs.
 */
import { strokePath } from "../canvas-objects.mjs";

/** The server's limits for a stroke: 2 to 256 points, each within ±10000 of
 * the stroke's position (API.md, canvas objects). */
export const MAX_POINTS = 256;
export const MAX_OFFSET = 10000;

// Adding 0 turns -0 into 0, so a first point is [0, 0], never [-0, 0].
const round1 = n => Math.round(n * 10) / 10 + 0;

function distanceToSegment([px, py], [ax, ay], [bx, by]) {
  const dx = bx - ax, dy = by - ay;
  const length = dx * dx + dy * dy;
  if (!length) return Math.hypot(px - ax, py - ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / length));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/**
 * Ramer, Douglas and Peucker: keep the first and last point, and any point
 * further than `tolerance` from the line between the points kept either side
 * of it. Iterative, so a long stroke cannot overflow the stack.
 */
export function simplify(points, tolerance = 0.75) {
  if (!Array.isArray(points) || points.length <= 2) return Array.isArray(points) ? points.slice() : [];
  const keep = new Uint8Array(points.length);
  keep[0] = keep[points.length - 1] = 1;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [first, last] = stack.pop();
    let index = -1, furthest = tolerance;
    for (let i = first + 1; i < last; i++) {
      const d = distanceToSegment(points[i], points[first], points[last]);
      if (d > furthest) { furthest = d; index = i; }
    }
    if (index > 0) { keep[index] = 1; stack.push([first, index], [index, last]); }
  }
  return points.filter((_, i) => keep[i]);
}

/** Simplified until it fits `max` points: the tolerance grows by half each
 * time, so a short stroke keeps its detail and only a long one is thinned. */
export function simplifyTo(points, max = MAX_POINTS, tolerance = 0.75) {
  let t = tolerance, out = simplify(points, t);
  while (out.length > max) { t *= 1.5; out = simplify(points, t); }
  return out;
}

/** A stroke's position is its first point and its points are offsets from
 * there, so the first is always [0, 0]; both to a tenth of a pixel. */
export function relativePoints(points) {
  if (!points?.length) return null;
  const x = round1(points[0][0]), y = round1(points[0][1]);
  return { x, y, points: points.map(([px, py]) => [round1(px - x), round1(py - y)]) };
}

/** The live stroke's path in world coordinates: the same smoothing the board
 * draws a saved stroke with, so the line does not change shape on release. */
export function smoothPath(points) {
  if (points?.length === 1) { const [x, y] = points[0]; return `M ${round1(x)} ${round1(y)} L ${round1(x)} ${round1(y)}`; }
  return strokePath(points);
}

/** Everything canvas.create needs for one drawn stroke, or null when there is
 * no line to save (one point, or a press that barely moved). */
export function strokeRecord(points, { max = MAX_POINTS, tolerance = 0.75, minLength = 3 } = {}) {
  if (!Array.isArray(points) || points.length < 2) return null;
  let length = 0;
  for (let i = 1; i < points.length; i++) length += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
  if (length < minLength) return null;
  const rel = relativePoints(simplifyTo(points, max, tolerance));
  // A stroke dragged further than the server allows from its start is cut
  // where it leaves the limit, rather than refused whole.
  const within = [];
  for (const p of rel.points) { if (Math.abs(p[0]) > MAX_OFFSET || Math.abs(p[1]) > MAX_OFFSET) break; within.push(p); }
  if (within.length < 2) return null;
  return { kind: "stroke", data: { points: within, weight: "regular", tone: "ink" }, x: rel.x, y: rel.y };
}

const SVG_NS = "http://www.w3.org/2000/svg";
function draftPath(board, d) {
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("class", "ink-stroke draft-stroke");
  if (d) path.setAttribute("d", d);
  board.draftLayer().append(path);
  return path;
}

export function register(registerTool) {
  registerTool("draw", {
    mount(ctx) {
      const board = ctx.board;
      if (!board) return;
      const pending = [];   // drawn and sent, not yet in the snapshot: {d, id, el}
      let live = null;

      const add = event => {
        const samples = event.getCoalescedEvents?.().length ? event.getCoalescedEvents() : [event];
        const minStep = 1.5 / board.view.z;
        for (const e of samples) {
          const p = board.toWorld(e.clientX, e.clientY);
          const last = live.points.at(-1);
          if (Math.hypot(p.x - last[0], p.y - last[1]) >= minStep) live.points.push([p.x, p.y]);
        }
        live.path.setAttribute("d", smoothPath(live.points));
      };
      const drop = () => { live?.path.remove(); live = null; };

      board.setToolHandler("draw", {
        down(event, hit) {
          if (hit.kind === "mark") return false;
          live = { points: [[hit.point.x, hit.point.y]] };
          live.path = draftPath(board, smoothPath(live.points));
          return true;
        },
        move(event) { if (live) add(event); },
        up(event) {
          if (!live) return;
          add(event);
          const record = strokeRecord(live.points);
          if (!record) { drop(); return; }
          const entry = { d: smoothPath(live.points), id: null, el: live.path };
          live = null;
          pending.push(entry);
          ctx.send("canvas.create", record).then(result => {
            entry.id = result?.item?.id ?? null;
            if (!entry.id) { entry.el?.remove(); pending.splice(pending.indexOf(entry), 1); }
          }).catch(() => {
            // send already put the reason in the banner; the line goes, so it
            // cannot look saved.
            entry.el?.remove();
            pending.splice(pending.indexOf(entry), 1);
          });
        },
        cancel: drop,
        leave: drop,
      });

      // Until the snapshot has a sent stroke, its draft is drawn again after
      // every render, so a redraw in between does not lose it.
      board.decorate((world, model) => {
        const drawn = new Set(model.objects.map(o => o.id));
        for (let i = pending.length - 1; i >= 0; i--) {
          if (pending[i].id && drawn.has(pending[i].id)) { pending.splice(i, 1); continue; }
          pending[i].el = draftPath(board, pending[i].d);
        }
      });

      board.setToolHandler("erase", {
        down(event, hit) {
          if (hit.kind !== "mark") return false;
          const record = board.snapshot?.records?.find(r => r.id === hit.id);
          if (!record) return true;
          const mark = board.root.querySelector(`.links [data-hit="${hit.id}"]`);
          mark?.classList.add("erased");
          ctx.send("canvas.remove", { item_id: record.id, expected_revision: record.revision })
            .catch(() => mark?.classList.remove("erased"));
          return true;
        },
      });
    },
  });
}
