/**
 * The parked margin: a shelf at the canvas's right edge (DESIGN.md 1.2).
 *
 * Owner: the phase 3 parked margin agent (DESIGN.md 1.5), with
 * css/parked.css and the <!-- region: parked --> block in index.html.
 *
 * What it is. A 200px band over the board's right edge where a note can be
 * put aside without being lost: dragged in, or parked with P, it leaves the
 * board and stands on the shelf as a compact card in its colour muted to
 * -soft; dragged back onto the board, or unparked with its button, it
 * returns. Parking is arranging, like a move, so it is never reviewed.
 *
 * Where it is kept. The shelf is a record of the canvas object model: a
 * `section` titled "Parked" with `form: "free"`, made by hand, created on
 * first use with `canvas.create` and changed with `canvas.update` on its
 * `member_ids`. Every screen reads the same record, so a note parked on one
 * screen is parked on all of them. The board would draw that section as a
 * rectangle; this tool hides it, and hides the parked notes, by marking the
 * board's own elements (`is-parked-section`, `is-parked`, `is-parked-link`)
 * after every board render.
 *
 * Contracts this relies on, all from DESIGN.md 0.2 and 2.5: a board note is
 * `.note[data-id]` inside `#board`, it carries `.dragging` while a person
 * drags it, and the drag ends with the board's own `item.place`; the board
 * instance exposes `view {x, y, z}`, `busy`, `selected` and `select(id,
 * additive)`; a note's accent is one `.note-{yellow,lilac,mint,periwinkle,
 * coral}` class from primitives.css.
 *
 * Everything above the "screen" divider is pure, so tests/parked-unit.mjs
 * runs it in Node without a browser.
 */

export const PARKED_TITLE = "Parked";
export const PARKED_FORM = "free";
/** The size the section record is given. It is never drawn at that size (the
 * band is), but the server requires a size for a section. */
export const PARKED_SIZE = { w: 200, h: 400 };
/** The server's limit on a section's members (API.md, Canvas objects). */
export const PARKED_MAX = 60;
/** How far right of the widest placed note the section record sits. */
const SECTION_GAP = 320 + 64;
const ACCENTS = ["yellow", "lilac", "mint", "periwinkle", "coral"];
const OPEN = ["needs_review", "stale"];

// ------------------------------------------------------------------ records

const recordOf = (snapshot, id) => (snapshot?.records ?? []).find(r => r.id === id) ?? null;

/** A section the shelf can stand on: accepted, made by a person, titled
 * Parked, free form. A model's section that happens to be titled Parked is
 * never adopted, because the shelf is a person's arrangement. */
export function isParkedSection(record) {
  const d = record?.data;
  return record?.kind === "item" && d?.item_kind === "section" && d.status === "accepted" &&
    d.title === PARKED_TITLE && d.form === PARKED_FORM && d.origin === "human" && d.made_by_hand === true;
}

/** Every Parked section, oldest first (then by id). Two screens parking the
 * first note at the same moment can make two; the oldest is the one new
 * notes go to, so every screen converges on the same record, and notes on the
 * other one still count as parked. */
export function parkedSections(snapshot) {
  return (snapshot?.records ?? []).filter(isParkedSection).sort((a, b) =>
    (a.data.created_at ?? 0) - (b.data.created_at ?? 0) || String(a.id).localeCompare(String(b.id)));
}

/** The section new notes are parked on, or null before first use. */
export function findParked(snapshot) {
  return parkedSections(snapshot)[0] ?? null;
}

/** On the canvas: an accepted item or an open proposal. The server refuses a
 * section member that is not (409 invalid_member), so a member that was
 * undone since is dropped from the next update rather than sent back. */
export function onCanvas(snapshot, id) {
  const r = recordOf(snapshot, id);
  if (!r) return false;
  if (r.kind === "item") return r.data?.status === "accepted" && r.data.item_kind !== "section";
  if (r.kind === "proposal") return OPEN.includes(r.data?.status);
  return false;
}

/** An accepted note: the only thing that parks. A proposal has to stay on the
 * board where the room can review it, and accepting one makes a new record,
 * so its id would leave the shelf anyway. */
export function isAcceptedNote(record) {
  const d = record?.data;
  return record?.kind === "item" && d?.status === "accepted" && d.item_kind === "content" && d.form !== "cluster";
}

/** The members of one section that are still on the canvas, in order. */
export function liveMembers(snapshot, section) {
  const ids = section?.data?.member_ids ?? [];
  return ids.filter((id, i) => ids.indexOf(id) === i && onCanvas(snapshot, id));
}

/** Parked note id -> the Parked section that holds it, in shelf order: the
 * oldest section's members first, each in the order they were parked. Only
 * accepted notes count; anything else in a Parked section is left alone. */
export function parkedNotes(snapshot) {
  const out = new Map();
  for (const section of parkedSections(snapshot)) {
    for (const id of liveMembers(snapshot, section)) {
      if (!out.has(id) && isAcceptedNote(recordOf(snapshot, id))) out.set(id, section);
    }
  }
  return out;
}

/** What else holds this note: an accepted group (cluster) or a section other
 * than Parked. A member belongs to one section (the canvas object model), and
 * a note in a group would leave a hole in its hull, so either refuses
 * parking. */
export function holderOf(snapshot, id) {
  for (const r of snapshot?.records ?? []) {
    if (r.kind !== "item" || r.data?.status !== "accepted") continue;
    if (r.data.form === "cluster" && (r.data.refs ?? []).some(ref => ref.id === id)) return { kind: "group", record: r };
    if (r.data.item_kind === "section" && !isParkedSection(r) && (r.data.member_ids ?? []).includes(id)) {
      return { kind: "section", record: r };
    }
  }
  return null;
}

/** Why a note cannot be parked, as the words the banner shows, or null when
 * it can. */
export function refusal(snapshot, id) {
  const r = recordOf(snapshot, id);
  if (!r) return "That note is no longer on the canvas.";
  if (!isAcceptedNote(r)) return "Only accepted notes can be parked. Review this one first.";
  if (holderOf(snapshot, id)) return "Take the note out of its group first.";
  return null;
}

// ----------------------------------------------------------------- payloads

/** `canvas.create` for the first parked note: the section is made with its
 * first member, so first use is one write. It sits to the right of every
 * placed note, level with the highest, out of the way of anything drawn. */
export function createPayload(snapshot, id) {
  const placed = (snapshot?.records ?? []).filter(r => r.position && Number.isFinite(r.position.x) && Number.isFinite(r.position.y));
  const x = placed.length ? Math.max(...placed.map(r => r.position.x + (r.position.w ?? 0))) + SECTION_GAP : 0;
  const y = placed.length ? Math.min(...placed.map(r => r.position.y)) : 0;
  return {
    kind: "section",
    data: { title: PARKED_TITLE, form: PARKED_FORM, member_ids: [id] },
    x: Math.round(x), y: Math.round(y), w: PARKED_SIZE.w, h: PARKED_SIZE.h,
  };
}

/** `canvas.update` adding one note to the end of the shelf, or null if it is
 * already there. Members no longer on the canvas are dropped. */
export function parkPayload(snapshot, section, id) {
  const members = liveMembers(snapshot, section);
  if (members.includes(id)) return null;
  return { item_id: section.id, expected_revision: section.revision, data: { member_ids: [...members, id] } };
}

/** `canvas.update` taking one note off the shelf, or null if it is not on
 * it. */
export function unparkPayload(snapshot, section, id) {
  const ids = section?.data?.member_ids ?? [];
  if (!ids.includes(id)) return null;
  const members = liveMembers(snapshot, section).filter(m => m !== id);
  return { item_id: section.id, expected_revision: section.revision, data: { member_ids: members } };
}

// ----------------------------------------------------------------- geometry

/** A point on the screen in the board's world coordinates. `view` is the
 * board's pan and zoom, {x, y, z}, in board pixels. */
export function toWorld(clientX, clientY, boardRect, view) {
  const z = view?.z || 1;
  return { x: (clientX - boardRect.left - (view?.x ?? 0)) / z, y: (clientY - boardRect.top - (view?.y ?? 0)) / z };
}

export function inside(rect, x, y) {
  return Boolean(rect) && rect.width > 0 && rect.height > 0 &&
    x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
}

/** Where on the screen a note unparked with its button lands: just left of
 * the band, level with its card, kept inside the board. The note was dropped
 * under the band, so leaving it there would hide it again. */
export function unparkPoint(boardRect, bandRect, cardRect, { noteWidth = 320, gap = 24, noteHeight = 120 } = {}) {
  const overlays = bandRect && bandRect.top < boardRect.bottom && bandRect.left > boardRect.left;
  const right = overlays ? bandRect.left : boardRect.right;
  const x = Math.max(boardRect.left + gap, right - gap - noteWidth);
  const top = cardRect ? cardRect.top : boardRect.top + gap;
  const y = Math.min(Math.max(top, boardRect.top + gap), Math.max(boardRect.top + gap, boardRect.bottom - gap - noteHeight));
  return { x, y };
}

/** The accent class of a board note, read from its classes, or null. */
export function accentOf(classList) {
  for (const name of classList ?? []) {
    const m = /^note-([a-z]+)$/.exec(name);
    if (m && ACCENTS.includes(m[1])) return m[1];
  }
  return null;
}

/** Words for a short announcement. */
export function shortWords(text, max = 48) {
  const t = String(text ?? "").replace(/\s+/g, " ").trim();
  return t.length > max ? `${t.slice(0, max - 1).trimEnd()}…` : t;
}

/** The shelf as the screen should show it: what the snapshot says, overlaid
 * with this screen's writes still waiting for the next poll (id -> true for
 * parked, false for unparked). The snapshot is only refreshed by polling, so
 * without this a parked note would stay on the board for up to a second. */
export function withPending(parked, pending) {
  const out = new Map(parked);
  for (const [id, on] of pending ?? []) {
    if (on && !out.has(id)) out.set(id, null);
    if (!on) out.delete(id);
  }
  return out;
}

// ------------------------------------------------------------------- screen

export function register(registerTool) {
  const state = {
    ctx: null, band: null, list: null, count: null, hint: null, status: null,
    parked: new Map(),        // note id -> section (null while its write is in flight)
    pending: new Map(),       // note id -> true (parking) or false (unparking), until a poll agrees
    signature: "",            // what the shelf last drew
    queue: Promise.resolve(), // writes run one at a time, each on the freshest snapshot
    lift: null,               // a card being dragged out
    target: false,            // a board note over the band: true, or the reason it cannot park
  };

  const board = () => state.ctx?.$("board");
  const snapshot = () => state.ctx?.app.snapshot;
  const closed = () => snapshot()?.session?.state === "closed";
  const usable = () => Boolean(state.band && !state.band.hidden);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  /** One write after another: a second park while the first is in flight
   * would carry a stale revision, or make a second Parked section. send()
   * already explains any refusal in the banner, so a failure here only stops
   * the chain from breaking. */
  function enqueue(job) {
    const run = state.queue.then(job);
    state.queue = run.catch(() => {});
    return state.queue;
  }

  /** Waits until the polled snapshot shows what was just written. Bounded:
   * a poll that never comes leaves the screen to catch up on its own. */
  async function until(test, ms = 4000) {
    const started = performance.now();
    while (!test(snapshot()) && performance.now() - started < ms) await sleep(50);
  }

  function announce(words) {
    if (state.status) state.status.textContent = words;
  }

  /** Recomputes the shelf and the board's marks from the snapshot and this
   * screen's pending writes. */
  function refreshView() {
    const s = snapshot();
    state.parked = withPending(parkedNotes(s), state.pending);
    markBoard();
    if (usable()) drawShelf(s);
  }

  // ---- marking the board -----------------------------------------------

  /** Hides the parked notes, the Parked section and any arrow to a parked
   * note on the board. Run after every render of the board, including the
   * renders the board makes by itself (a drag ending, details opening), so
   * it watches the board's DOM rather than waiting for the tool hook. */
  function markBoard() {
    const root = board();
    if (!root) return;
    const s = snapshot();
    const sections = new Set(parkedSections(s).map(r => r.id));
    const links = new Set();
    for (const r of s?.records ?? []) {
      const item = r.kind === "item";
      const kind = item ? r.data?.item_kind : r.data?.canvas_kind;
      const d = item ? r.data : r.data?.canvas_data;
      if (kind !== "arrow" || !d) continue;
      if (state.parked.has(d.from?.id) || state.parked.has(d.to?.id)) links.add(r.id);
    }
    let changed = false;
    for (const el of root.querySelectorAll("[data-id]")) {
      const id = el.dataset.id;
      const isNote = el.classList.contains("note");
      changed = flip(el, "is-parked", isNote && state.parked.has(id)) || changed;
      changed = flip(el, "is-parked-section", !isNote && sections.has(id)) || changed;
      changed = flip(el, "is-parked-link", !isNote && links.has(id)) || changed;
    }
    // Until a person pans or zooms, the board fits itself on every render,
    // and that fit runs before this marking hides the parked notes: it
    // fitted notes nobody could see and held the wall at 52% where 77% fits
    // (phase 5 review). Fit again once they are hidden; fit() only moves the
    // world, so this observer is not woken by it.
    const live = state.ctx?.board;
    if (changed && live && !live.view.touched) live.fit();
  }
  const flip = (el, name, on) => {
    if (el.classList.contains(name) === on) return false;
    el.classList.toggle(name, on);
    return true;
  };

  // ---- the shelf -------------------------------------------------------

  function build(band) {
    band.textContent = "";
    const head = document.createElement("div");
    head.className = "parked-head";
    const title = document.createElement("h2");
    title.className = "parked-title";
    title.id = "parked-title";
    title.textContent = PARKED_TITLE;
    const count = document.createElement("span");
    count.className = "parked-count";
    count.setAttribute("aria-hidden", "true");
    head.append(title, count);
    const hint = document.createElement("p");
    hint.className = "parked-hint";
    const list = document.createElement("ol");
    list.className = "parked-list";
    list.setAttribute("aria-labelledby", "parked-title");
    const status = document.createElement("p");
    status.className = "visually-hidden";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    band.append(head, hint, list, status);
    Object.assign(state, { band, list, count, hint, status });
  }

  function hintWords() {
    if (state.target) return state.target === true ? "Release to park" : state.target;
    if (state.parked.size) return "";
    return closed() ? "Nothing was parked" : "Drag a note here to park it";
  }

  function paintHint() {
    const words = hintWords();
    state.hint.textContent = words;
    state.hint.hidden = !words;
    state.band.classList.toggle("is-target", state.target === true);
  }

  function drawShelf(s) {
    const root = board();
    const items = [...state.parked.keys()].map(id => {
      const el = root?.querySelector(`.note[data-id="${CSS.escape(id)}"]`);
      return { id, text: recordOf(s, id)?.data?.text ?? "", accent: accentOf(el?.classList) ?? "yellow" };
    });
    paintHint();
    state.count.textContent = items.length ? String(items.length) : "";
    const signature = JSON.stringify([items, closed()]);
    if (signature === state.signature || state.lift) return;
    state.signature = signature;

    const focused = document.activeElement?.closest?.("#parked [data-parked-id]")?.dataset.parkedId ?? null;
    state.list.textContent = "";
    for (const item of items) {
      const li = document.createElement("li");
      const card = document.createElement("article");
      card.className = `parked-card note-${item.accent}`;
      card.dataset.parkedId = item.id;
      const text = document.createElement("p");
      text.className = "parked-text";
      text.textContent = item.text;
      card.append(text);
      if (!closed()) {
        const unpark = document.createElement("button");
        unpark.type = "button";
        unpark.className = "btn btn-quiet btn-sm parked-unpark";
        unpark.textContent = "Unpark";
        unpark.setAttribute("aria-label", `Unpark “${shortWords(item.text)}”`);
        unpark.addEventListener("click", () => unparkWithButton(item.id, card));
        card.append(unpark);
        wireLift(card, item.id);
      }
      li.append(card);
      state.list.append(li);
    }
    if (focused) state.list.querySelector(`[data-parked-id="${CSS.escape(focused)}"] .parked-unpark`)?.focus();
  }

  // ---- parking and unparking -------------------------------------------

  function park(id) {
    return enqueue(async () => {
      const { ctx } = state;
      const s = snapshot();
      try {
        if (!s || closed() || parkedNotes(s).has(id)) return;
        const why = refusal(s, id);
        if (why) { ctx.attention(why, "note"); return; }
        const section = findParked(s);
        if (section && liveMembers(s, section).length >= PARKED_MAX) {
          ctx.attention(`The shelf holds ${PARKED_MAX} notes. Unpark one before parking another.`, "note");
          return;
        }
        state.pending.set(id, true);
        refreshView();
        if (!section) await ctx.send("canvas.create", createPayload(s, id));
        else await ctx.send("canvas.update", parkPayload(s, section, id));
        // A parked note is not on the board, so it cannot stay selected there.
        if (ctx.board?.selected?.has(id)) ctx.board.select(id, true);
        announce(`Parked “${shortWords(recordOf(s, id)?.data?.text)}”.`);
        await until(fresh => parkedNotes(fresh).has(id));
      } finally {
        state.pending.delete(id);
        refreshView();
      }
    });
  }

  /** Off the shelf; with a world point, put on the board there first, so the
   * note appears where it lands rather than at the place it was parked from. */
  function unpark(id, point) {
    return enqueue(async () => {
      const { ctx } = state;
      const s = snapshot();
      const r = recordOf(s, id);
      if (!s || !r || closed() || !parkedNotes(s).has(id)) return;
      try {
        if (point) {
          const before = r.position?.revision ?? 0;
          await ctx.send("item.place", { placements: [{ id, x: Math.round(point.x), y: Math.round(point.y),
            expected_position_revision: before }] });
          await until(fresh => (recordOf(fresh, id)?.position?.revision ?? 0) !== before);
        }
        state.pending.set(id, false);
        refreshView();
        const now = snapshot();
        const section = parkedNotes(now).get(id);
        const payload = section && unparkPayload(now, recordOf(now, section.id) ?? section, id);
        if (payload) await ctx.send("canvas.update", payload);
        announce(`Unparked “${shortWords(r.data?.text)}”.`);
        await until(fresh => !parkedNotes(fresh).has(id));
      } finally {
        state.pending.delete(id);
        refreshView();
      }
    });
  }

  async function unparkWithButton(id, card) {
    const root = board();
    if (!root || root.hidden) return;
    const li = card.closest("li");
    const nextId = (li?.nextElementSibling ?? li?.previousElementSibling)?.querySelector("[data-parked-id]")?.dataset.parkedId;
    const rect = root.getBoundingClientRect();
    const at = unparkPoint(rect, state.band.getBoundingClientRect(), card.getBoundingClientRect());
    await unpark(id, toWorld(at.x, at.y, rect, state.ctx.board?.view));
    // Focus stays on the shelf while there is more on it, else returns to the board.
    const again = nextId && state.list.querySelector(`[data-parked-id="${CSS.escape(nextId)}"] .parked-unpark`);
    (again || root).focus();
  }

  /** Resolves once the board has finished its own drag: its item.place has
   * answered and it has redrawn. Bounded, so a board that never says it is
   * idle cannot hold the park forever. */
  async function boardSettled() {
    const frame = () => new Promise(resolve => requestAnimationFrame(() => resolve()));
    const started = performance.now();
    await frame();
    while (state.ctx.board?.busy && performance.now() - started < 5000) await sleep(40);
    await frame();
  }

  // ---- dragging a board note in ----------------------------------------
  // The board captures the pointer on the note it drags, so the band itself
  // never receives pointerenter or pointerup during that drag. The document
  // does, in the capture phase, before the note's own handler clears
  // .dragging; so the band listens there and tests its own rectangle.

  function dragged() {
    return board()?.querySelector(".note.dragging[data-id]") ?? null;
  }

  function overBand(event) {
    return usable() && inside(state.band.getBoundingClientRect(), event.clientX, event.clientY);
  }

  /** What may stop a dragged note parking. A group is not a reason here: a
   * drag out of a group's hull takes the note out of the group (the board
   * does that), so the drop parks it once that has happened. */
  function dropRefusal(s, id) {
    const r = recordOf(s, id);
    if (!isAcceptedNote(r)) return refusal(s, id);
    return holderOf(s, id)?.kind === "section" ? refusal(s, id) : null;
  }

  function setTarget(value) {
    if (state.target === value) return;
    state.target = value;
    if (state.band) paintHint();
  }

  function wireDragIn() {
    document.addEventListener("pointermove", event => {
      const note = dragged();
      if (!note || closed() || !overBand(event)) { setTarget(false); return; }
      setTarget(dropRefusal(snapshot(), note.dataset.id) ?? true);
    }, true);
    document.addEventListener("pointerup", event => {
      const note = dragged();
      setTarget(false);
      if (!note || closed() || !overBand(event)) return;
      const id = note.dataset.id;
      const s = snapshot();
      const why = dropRefusal(s, id);
      const grouped = holderOf(s, id)?.kind === "group";
      if (!why) {
        // Off the board at once, after the board's own handler has read
        // where the note was let go.
        setTimeout(() => { state.pending.set(id, true); refreshView(); }, 0);
      }
      boardSettled()
        .then(() => grouped ? until(fresh => holderOf(fresh, id)?.kind !== "group", 3000) : null)
        // park() clears the optimistic mark itself, whatever it decides, so
        // the note cannot flash back onto the board while it waits its turn.
        .then(() => why ? state.ctx.attention(why, "note") : park(id));
    }, true);
    document.addEventListener("pointercancel", () => setTarget(false), true);
  }

  // ---- dragging a card out ---------------------------------------------

  function wireLift(card, id) {
    card.addEventListener("pointerdown", event => {
      if (event.button !== 0 || event.target.closest("button") || state.ctx.board?.readonly || closed()) return;
      const rect = card.getBoundingClientRect();
      state.lift = { id, card, x: event.clientX, y: event.clientY,
        dx: event.clientX - rect.left, dy: event.clientY - rect.top, ghost: null };
      card.setPointerCapture(event.pointerId);
    });
    card.addEventListener("pointermove", event => {
      const lift = state.lift;
      if (!lift || lift.card !== card) return;
      if (!lift.ghost) {
        if (Math.abs(event.clientX - lift.x) + Math.abs(event.clientY - lift.y) <= 3) return;
        const rect = card.getBoundingClientRect();
        lift.ghost = card.cloneNode(true);
        lift.ghost.classList.add("parked-ghost");
        lift.ghost.removeAttribute("data-parked-id");
        lift.ghost.setAttribute("aria-hidden", "true");
        lift.ghost.style.width = `${rect.width}px`;
        card.classList.add("is-lifted");
        state.band.append(lift.ghost);
      }
      lift.ghost.style.left = `${event.clientX - lift.dx}px`;
      lift.ghost.style.top = `${event.clientY - lift.dy}px`;
    });
    const end = event => {
      const lift = state.lift;
      if (!lift || lift.card !== card) return;
      state.lift = null;
      lift.ghost?.remove();
      card.classList.remove("is-lifted");
      const root = board();
      const rect = root?.getBoundingClientRect();
      const onBoard = lift.ghost && event.type === "pointerup" && root && !root.hidden &&
        inside(rect, event.clientX, event.clientY) && !overBand(event);
      if (!onBoard) { refreshView(); return; }
      // The note's top left goes where the card's top left was let go.
      unpark(lift.id, toWorld(event.clientX - lift.dx, event.clientY - lift.dy, rect, state.ctx.board?.view));
    };
    card.addEventListener("pointerup", end);
    card.addEventListener("pointercancel", end);
  }

  // ---- the P key -------------------------------------------------------

  function wireKey() {
    document.addEventListener("keydown", event => {
      if (event.key !== "p" && event.key !== "P") return;
      if (event.ctrlKey || event.metaKey || event.altKey || event.defaultPrevented || event.repeat) return;
      const active = document.activeElement;
      const root = board();
      if (!active || !root || !root.contains(active) || !usable() || closed()) return;
      if (active.closest("input, textarea, select, [contenteditable=''], [contenteditable='true']")) return;
      let id = active.closest(".note[data-id]")?.dataset.id ?? null;
      const selected = state.ctx.board?.selected;
      if (!id && active === root && selected?.size === 1) id = [...selected][0];
      if (!id) return;
      event.preventDefault();
      // The note leaves the board, and focus with it; it returns to the board.
      park(id).then(() => { if (!root.contains(document.activeElement) || document.activeElement === document.body) root.focus(); });
      if (active !== root) root.focus();
    });
  }

  registerTool("parked", {
    mount(ctx) {
      state.ctx = ctx;
      const band = ctx.$("parked");
      if (!band) return;
      build(band);
      wireDragIn();
      wireKey();
      const root = ctx.$("board");
      if (root) new MutationObserver(() => markBoard()).observe(root, { childList: true, subtree: true });
    },
    render(ctx) {
      if (!state.band) return;
      ctx.show(state.band, ctx.app.screen === "workspace" && ctx.app.view === "canvas" &&
        !(ctx.app.board?.isTopicLayout() && parkedNotes(snapshot()).size === 0));
      refreshView();
    },
  });
}
