/**
 * The connector tool (DESIGN.md 1.2): press one note or shape, then another,
 * to relate them. The board draws the connector as a clean cubic curve
 * between the nearest sides of the two (canvas-objects.mjs,
 * connectorGeometry). After the second press a small field opens at the
 * curve's middle for an optional label: Enter saves it with the label,
 * Escape saves it without one. It persists as an `arrow` record through
 * `canvas.create` with `tone: "ink"`, accepted at once like any hand-drawn
 * object.
 *
 * Undirected by default: no head. Holding Shift on the second press makes it
 * directed, drawn with an open chevron at its end. The `arrow` kind has no
 * direction field and the backend is out of scope, so direction is kept on
 * this device: a set of arrow ids in localStorage under
 * `jv.connectors.directed`. Another device draws the same connector
 * undirected, which is the default look, so it never claims a direction it
 * does not know. Arrows that existed before this tool, which used to be drawn
 * with a head, are undirected curves unless their id is in the set. Setting
 * `jv.flags.connectorDirection` to "off" turns Shift's direction off.
 *
 * If localStorage cannot be used (a private window, storage blocked), the set
 * is kept in memory for this page and one quiet note says so, once.
 *
 * Escape before the second press, choosing another tool, or pressing the
 * first end again cancels.
 */
import { connectorGeometry, connectorHead } from "../canvas-objects.mjs";

export const DIRECTED_KEY = "jv.connectors.directed";
export const DIRECTION_FLAG = "jv.flags.connectorDirection";
export const MEMORY_NOTE = "Connector direction is kept on this device only.";
const LABEL_MAX = 80;   // the server's limit for an arrow's label

/**
 * The set of directed connector ids, kept in `getStorage()` (localStorage in
 * the page, a fake in tests). Reading or writing that throws switches it to
 * memory for the rest of the page and calls `onMemoryOnly` once, at the first
 * directed connector made after that. Garbage under the key reads as an empty
 * set, because a corrupt list is no reason to stop saving.
 */
export function createDirectedStore(getStorage, { onMemoryOnly = () => {}, limit = 1000 } = {}) {
  let ids = new Set(), memoryOnly = false, told = false;
  try {
    const raw = getStorage().getItem(DIRECTED_KEY);
    try {
      const list = raw ? JSON.parse(raw) : [];
      if (Array.isArray(list)) ids = new Set(list.filter(id => typeof id === "string"));
    } catch { ids = new Set(); }
  } catch { memoryOnly = true; }
  const save = () => {
    if (memoryOnly) return;
    try { getStorage().setItem(DIRECTED_KEY, JSON.stringify([...ids].slice(-limit))); }
    catch { memoryOnly = true; }
  };
  const tell = () => { if (memoryOnly && !told) { told = true; onMemoryOnly(); } };
  return {
    has: id => ids.has(id),
    add(id) { ids.add(id); save(); tell(); },
    delete(id) { if (ids.delete(id)) save(); },
    get size() { return ids.size; },
    get memoryOnly() { return memoryOnly; },
  };
}

/** Whether Shift may make a connector directed: on unless the flag says off. */
export function directionEnabled(getStorage) {
  try { return getStorage().getItem(DIRECTION_FLAG) !== "off"; } catch { return true; }
}

/** The canvas.create payload for one connector. Its position is the curve's
 * middle, which the server stores and the client ignores for arrows. */
export function connectorPayload(fromId, toId, label, mid) {
  const words = String(label ?? "").trim().slice(0, LABEL_MAX);
  return { kind: "arrow", data: { from: { id: fromId }, to: { id: toId }, tone: "ink", ...(words ? { label: words } : {}) },
    x: Math.round(mid?.x ?? 0), y: Math.round(mid?.y ?? 0) };
}

const SVG_NS = "http://www.w3.org/2000/svg";
const path = (cls, d) => {
  const p = document.createElementNS(SVG_NS, "path");
  p.setAttribute("class", cls);
  p.setAttribute("d", d);
  return p;
};

export function register(registerTool) {
  registerTool("connect", {
    mount(ctx) {
      const board = ctx.board;
      if (!board) return;
      const storage = () => window.localStorage;
      const store = createDirectedStore(storage, { onMemoryOnly: () => ctx.attention(MEMORY_NOTE, "note") });
      board.directed = store;

      let from = null;      // the first end's id
      let pointer = null;   // the last pointer position, for the preview
      let open = null;      // {to, directed, curve, field, input, release, done}

      const endEl = id => board.world.querySelector(`.note[data-id="${CSS.escape(id)}"], .cobj[data-id="${CSS.escape(id)}"]`);
      const mark = () => {
        for (const el of board.world.querySelectorAll(".connect-from")) el.classList.remove("connect-from");
        if (from) endEl(from)?.classList.add("connect-from");
      };
      const drawPreview = () => {
        for (const el of board.world.querySelectorAll(".connector-preview, .connector-draft")) el.remove();
        if (open) {
          const layer = board.draftLayer();
          layer.append(path("connector connector-draft", open.curve.d));
          if (open.directed) layer.append(path("connector-head connector-directed connector-draft", connectorHead(open.curve)));
          return;
        }
        const box = from && board.boxOf(from);
        if (!box || !pointer) return;
        const curve = connectorGeometry(box, pointer);
        if (curve) board.draftLayer().append(path("connector connector-preview", curve.d));
      };
      const cancel = () => { from = null; pointer = null; mark(); drawPreview(); };

      const finish = (label, save = true) => {
        if (!open || open.done) return;
        const { to, directed, curve, field, release } = open;
        open.done = true;
        const start = from;
        open = null;
        field.remove();
        from = null; pointer = null;
        mark(); drawPreview();
        release();
        if (!save) return;
        ctx.send("canvas.create", connectorPayload(start, to, label, curve.mid)).then(result => {
          const id = result?.item?.id;
          if (directed && id) { store.add(id); board.render(board.snapshot); }
        }).catch(() => {});
      };

      const askLabel = (to, directed) => {
        const a = board.boxOf(from), b = board.boxOf(to);
        const curve = a && b && connectorGeometry(a, b);
        if (!curve) {
          ctx.attention("These two overlap, so a connector between them could not be drawn. Move one of them first.", "note");
          cancel();
          return;
        }
        const field = document.createElement("div");
        field.className = "cobj-float cobj-float-middle connector-field";
        field.style.left = `${curve.mid.x}px`;
        field.style.top = `${curve.mid.y}px`;
        const input = document.createElement("input");
        input.className = "connector-input";
        input.maxLength = LABEL_MAX;
        input.placeholder = "Label";
        input.setAttribute("aria-label", "Label for this connector. Enter saves it, Escape saves it without a label.");
        field.append(input);
        open = { to, directed, curve, field, input, release: board.hold(), done: false };
        board.world.append(field);
        drawPreview();
        input.addEventListener("keydown", event => {
          if (event.key === "Enter") { event.preventDefault(); finish(input.value); }
          else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); finish(""); }
        });
        input.addEventListener("blur", () => finish(input.value));
        input.focus();
      };

      board.setToolHandler("connect", {
        down(event, hit) {
          if (open) return false;
          if (!hit.id || !["note", "object"].includes(hit.kind)) return false;
          if (!from) { from = hit.id; pointer = hit.point; mark(); return true; }
          if (hit.id === from) { cancel(); return true; }
          // A press on a note would also focus it and steal the field's focus
          // once the field opens, so the field opens after this press ends.
          event.preventDefault();
          const to = hit.id, directed = event.shiftKey && directionEnabled(storage);
          setTimeout(() => askLabel(to, directed), 0);
          return true;
        },
        hover(event, point) { if (from && !open) { pointer = point; drawPreview(); } },
        leave() { if (open) finish(open.input.value); else cancel(); },
      });

      // A redraw replaces the world; the first end's mark and the preview are
      // put back. (The field is held still by board.hold while it is open.)
      board.decorate(() => { mark(); drawPreview(); });

      document.addEventListener("keydown", event => {
        if (event.key === "Escape" && board.tool === "connect" && from && !open) cancel();
      });
    },
  });
}
