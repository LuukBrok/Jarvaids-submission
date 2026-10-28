/**
 * Provenance threads: lines from the selected note to where it came from
 * (DESIGN.md 1.2, signature move 1).
 *
 * Owner: the phase 3 provenance threads agent (DESIGN.md 1.5).
 *
 * When notes are selected, each one gets a thin curve, in page space, from
 * the nearest edge of its rectangle on screen to each of its origins that is
 * on screen, ending in a small dot at the origin:
 *
 *   crop         the photograph crop in its review card, or in its own open
 *                details
 *   transcript   the transcript line a quote note was pulled from
 *   person       the People row of the person who accepted it
 *   group        the outline of the group or section it belongs to
 *   connector    each connector that starts or ends at it
 *
 * An origin that is not on screen (its rail tab is not shown, it is scrolled
 * out of view, it is covered, or it is not in the page) gets no thread, so a
 * thread never points at nothing. A note with no origins gets none, which is
 * the point: a note nobody has substantiated visibly has no lines leaving it.
 *
 * Everything is read from what the snapshot already holds (`refs`,
 * `member_ids`, `region_id`, `accepted_by`, `proposal_id`) and the quote
 * links in localStorage; nothing is persisted. The record shapes are read
 * here rather than through board.mjs or canvas-objects.mjs, because those
 * are being rebuilt in parallel and this tool must keep working whatever
 * their exports become: only the markup contracts are relied on.
 *
 * Nothing runs while nothing is selected: the listeners and the observer are
 * attached on the first selection and removed when it empties. While a
 * selection exists, positions are recomputed at most once per animation
 * frame, on zoom and pan, on scroll of the rail or the window, on pointer
 * move while a drag is in progress, on every render, and when a class or
 * `hidden` changes (a rail tab, the strip's scrubbing). Nothing animates.
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/** Where the quote tool keeps note id to {segmentId, time, speakerActorId}. */
export const LINKS_KEY = "jv.quotes.links";

/** A thread never leaves a rectangle closer to a corner than this, in px,
 * because a curve that starts on a corner reads as belonging to neither side. */
const CORNER_INSET = 8;
/** How far the curve's control points pull away from each end: a share of
 * the distance, capped so a long thread does not bow out across the page. */
const PULL_SHARE = 0.4, PULL_MAX = 160;

const OPEN = ["needs_review", "stale"];

// ------------------------------------------------------------------ geometry

const round = n => Math.round(n * 100) / 100;

export function centre(rect) {
  return { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 };
}

/**
 * The point on a rectangle's edge that faces `toward`, and the unit normal of
 * that edge oriented toward `toward`, as {x, y, nx, ny}.
 *
 * Outside the rectangle, the edge is the one a ray from the centre to the
 * point leaves through, and the point slides along that edge to be as close
 * to `toward` as it can, kept CORNER_INSET from the corners. Inside it (a
 * note within its group's outline), the edge is the nearest one and the
 * normal points inward, so a curve from it heads for the point.
 */
export function edgeToward(rect, toward) {
  const c = centre(rect);
  const dx = toward.x - c.x, dy = toward.y - c.y;
  const a = rect.w / 2, b = rect.h / 2;
  const inside = Math.abs(dx) <= a && Math.abs(dy) <= b;
  let side;
  if (inside) {
    const gaps = { left: toward.x - rect.x, right: rect.x + rect.w - toward.x,
      top: toward.y - rect.y, bottom: rect.y + rect.h - toward.y };
    side = Object.keys(gaps).reduce((best, k) => (gaps[k] < gaps[best] ? k : best));
  } else {
    const horizontal = a === 0 || (b !== 0 && Math.abs(dx) / a >= Math.abs(dy) / b);
    side = horizontal ? (dx < 0 ? "left" : "right") : (dy < 0 ? "top" : "bottom");
  }
  const along = (value, start, length) => {
    const inset = Math.min(CORNER_INSET, length / 2);
    return Math.min(start + length - inset, Math.max(start + inset, value));
  };
  const outward = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] }[side];
  const flip = inside ? -1 : 1;
  const [nx, ny] = [outward[0] * flip + 0, outward[1] * flip + 0];   // + 0 turns -0 into 0
  if (side === "left" || side === "right") {
    return { x: side === "left" ? rect.x : rect.x + rect.w, y: along(toward.y, rect.y, rect.h), nx, ny };
  }
  return { x: along(toward.x, rect.x, rect.w), y: side === "top" ? rect.y : rect.y + rect.h, nx, ny };
}

/** Both ends of one thread: the origin's edge facing the note's centre, then
 * the note's edge facing that point. The origin end is found first so that a
 * group outline around the note is reached at its nearest side. */
export function threadEnds(noteRect, originRect) {
  const origin = edgeToward(originRect, centre(noteRect));
  const note = edgeToward(noteRect, origin);
  return { note, origin };
}

/** A cubic curve from `a` to `b` that leaves and enters along each end's
 * normal, as an SVG path string with coordinates to two decimals. */
export function threadPath(a, b) {
  const pull = Math.min(PULL_MAX, Math.hypot(b.x - a.x, b.y - a.y) * PULL_SHARE);
  const p = (x, y) => `${round(x)} ${round(y)}`;
  return `M ${p(a.x, a.y)} C ${p(a.x + a.nx * pull, a.y + a.ny * pull)} ` +
    `${p(b.x + b.nx * pull, b.y + b.ny * pull)} ${p(b.x, b.y)}`;
}

// ------------------------------------------------------------------- origins

/** The quote links, or an empty object if there are none or they are not an
 * object: a broken entry another tool wrote must not take the threads down. */
export function readLinks(storage) {
  try {
    const value = JSON.parse(storage?.getItem(LINKS_KEY) ?? "null");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

/** A drawable canvas object of `kind` from a record, as its fields, or null.
 * An item keeps them on `data`; an open canvas proposal on `canvas_data`. */
function canvasFields(record, kind) {
  const d = record?.data;
  if (!d) return null;
  if (record.kind === "item" && d.item_kind === kind && d.status === "accepted") return d;
  if (record.kind === "proposal" && d.proposal_kind === "canvas" && d.canvas_kind === kind && OPEN.includes(d.status)) {
    return d.canvas_data ?? {};
  }
  return null;
}

function isNote(r) {
  const d = r?.data;
  if (!d || d.form === "cluster") return false;
  return (r.kind === "item" && d.status === "accepted" && d.item_kind === "content") ||
    (r.kind === "proposal" && d.proposal_kind === "content" && OPEN.includes(d.status));
}

function isGroup(r) {
  const d = r?.data;
  if (d?.form !== "cluster") return false;
  return (r.kind === "item" && d.status === "accepted") ||
    (r.kind === "proposal" && d.proposal_kind === "relationship" && OPEN.includes(d.status));
}

/**
 * Where one note came from, as a list of origins in drawing order, from the
 * snapshot and the quote links alone. Each origin is {kind, ...}:
 *
 *   {kind: "crop", ids}             ids: the note's id, and the proposal it was
 *                                   accepted from, either of which may have a card
 *   {kind: "transcript", segmentId}
 *   {kind: "person", actorId}
 *   {kind: "group", id}             a cluster (accepted or proposed) or a section
 *   {kind: "connector", id}         an arrow with this note at either end
 *
 * An accepted item answers to its own id and to `data.proposal_id`, because
 * a link, a group or an arrow made before acceptance names the proposal.
 */
export function resolveOrigins(noteId, snapshot, links = {}) {
  const records = snapshot?.records ?? [];
  const note = records.find(r => r.id === noteId);
  if (!isNote(note)) return [];
  const d = note.data;
  const aliases = [note.id, note.kind === "item" ? d.proposal_id : null].filter(id => typeof id === "string" && id);
  const named = id => aliases.includes(id);
  const origins = [];

  if (d.region_id) origins.push({ kind: "crop", ids: aliases });
  const link = aliases.map(id => links?.[id]).find(l => l && typeof l.segmentId === "string" && l.segmentId);
  if (link) origins.push({ kind: "transcript", segmentId: link.segmentId });
  if (note.kind === "item" && typeof d.accepted_by === "string" && d.accepted_by) {
    origins.push({ kind: "person", actorId: d.accepted_by });
  }
  for (const r of records) {
    if (isGroup(r) && (r.data.refs ?? []).some(ref => named(ref?.id))) origins.push({ kind: "group", id: r.id });
    const section = canvasFields(r, "section");
    if (section && Array.isArray(section.member_ids) && section.member_ids.some(named)) origins.push({ kind: "group", id: r.id });
  }
  for (const r of records) {
    const arrow = canvasFields(r, "arrow");
    if (arrow && (named(arrow.from?.id) || named(arrow.to?.id))) origins.push({ kind: "connector", id: r.id });
  }
  return origins;
}

/** An attribute value for a selector, quoted. */
const q = value => `"${String(value).replace(/["\\]/g, "\\$&")}"`;

/**
 * Where to look for an origin on the page, in order of preference, as
 * {scope, selector, svgOnly?}. `scope` is "page" (the rail and anything else
 * outside the canvas) or "board" (inside the board's root). These are the
 * markup contracts this tool relies on; DESIGN.md 1.2 lists them.
 */
export function originSelectors(origin, noteId) {
  switch (origin.kind) {
    case "crop": return [
      ...origin.ids.map(id => ({ scope: "page", selector: `.proposal[data-id=${q(id)}] img` })),
      { scope: "board", selector: `.note[data-id=${q(noteId)}] .crop img` },
    ];
    case "transcript": return [
      { scope: "page", selector: `[id=${q(`seg-${origin.segmentId}`)}]` },
      { scope: "page", selector: `.transcript-row[data-segment-id=${q(origin.segmentId)}]` },
    ];
    case "person": return [{ scope: "page", selector: `.person[data-actor-id=${q(origin.actorId)}]` }];
    case "group": return [
      { scope: "board", selector: `.hull[data-id=${q(origin.id)}]` },
      // Sections are drawn as their own outline today, not a .hull.
      { scope: "board", selector: `[data-id=${q(origin.id)}]:not(.note)` },
    ];
    case "connector": return [{ scope: "board", selector: `[data-id=${q(origin.id)}]`, svgOnly: true }];
    default: return [];
  }
}

// ----------------------------------------------------------------- coalescer

/** Runs `fn` at most once per animation frame however often it is asked. */
export function createCoalescer(fn, raf = globalThis.requestAnimationFrame?.bind(globalThis),
  caf = globalThis.cancelAnimationFrame?.bind(globalThis)) {
  let handle = null, waiting = false;
  return {
    schedule() {
      if (waiting) return false;
      waiting = true;
      handle = raf(() => { waiting = false; handle = null; fn(); });
      return true;
    },
    cancel() {
      if (!waiting) return;
      waiting = false;
      caf?.(handle);
      handle = null;
    },
    get pending() { return waiting; },
  };
}

// ------------------------------------------------------------------ the page

/** The part of an element that can be seen, as {x, y, w, h} in page (client)
 * pixels, or null: not in the page, not rendered (a hidden rail tab), or
 * clipped away by the viewport or by an ancestor that clips (the rail's
 * scroll, the board's edge). */
export function visibleRect(el, win = globalThis.window) {
  if (!el?.isConnected) return null;
  if (typeof el.checkVisibility === "function" && !el.checkVisibility({ visibilityProperty: true })) return null;
  if (!el.getClientRects().length) return null;
  const r = el.getBoundingClientRect();
  let box = { l: r.left, t: r.top, r: r.right, b: r.bottom };
  const clip = c => {
    box = { l: Math.max(box.l, c.left), t: Math.max(box.t, c.top), r: Math.min(box.r, c.right), b: Math.min(box.b, c.bottom) };
  };
  // A straight connector is wide and nearly flat, so a box is gone only when
  // it is negative either way or under a pixel both ways.
  const gone = () => box.r - box.l < 0 || box.b - box.t < 0 || (box.r - box.l < 1 && box.b - box.t < 1);
  clip({ left: 0, top: 0, right: win.innerWidth, bottom: win.innerHeight });
  for (let a = el.parentElement; a && a !== el.ownerDocument.documentElement; a = a.parentElement) {
    if (gone()) return null;
    const cs = win.getComputedStyle(a);
    if (cs.overflowX !== "visible" || cs.overflowY !== "visible") clip(a.getBoundingClientRect());
    if (cs.position === "fixed") break;
  }
  if (gone()) return null;
  return { x: box.l, y: box.t, w: box.r - box.l, h: box.b - box.t };
}

/**
 * The threads controller, separate from the registry so a test can drive it.
 *
 *   svg          the page-space layer (#threads)
 *   getBoard()   the Board (its `root`, `snapshot` and `busy` are read)
 *   getSnapshot() the snapshot, when the board has none
 *   storage      where the quote links are (localStorage)
 */
export function createThreads({ svg, getBoard = () => null, getSnapshot = () => null,
  storage = globalThis.localStorage, win = globalThis.window, raf, caf } = {}) {
  const doc = win.document;
  let selection = [];
  let attached = false;
  // Looked up at each call, not bound once, so whatever the page's frame
  // function is at the time (a test counting frames, say) is the one used.
  const frame = createCoalescer(draw, raf ?? (fn => win.requestAnimationFrame(fn)),
    caf ?? (id => win.cancelAnimationFrame(id)));

  const schedule = () => { if (selection.length) frame.schedule(); };
  const onPointerMove = event => {
    // Only while something is being dragged or panned: a plain hover moves nothing.
    if (event.buttons || getBoard()?.busy) schedule();
  };
  const observer = typeof win.MutationObserver === "function" ? new win.MutationObserver(records => {
    // The layer's own changes are not news.
    if (records.some(r => !svg.contains(r.target))) schedule();
  }) : null;

  function attach() {
    if (attached) return;
    attached = true;
    doc.addEventListener("scroll", schedule, { capture: true, passive: true });
    doc.addEventListener("pointermove", onPointerMove, { passive: true });
    doc.addEventListener("load", schedule, true);   // a crop image arriving changes the layout
    win.addEventListener("resize", schedule);
    observer?.observe(doc.body, { attributes: true, attributeFilter: ["class", "hidden"], subtree: true });
  }

  function detach() {
    if (!attached) return;
    attached = false;
    doc.removeEventListener("scroll", schedule, { capture: true });
    doc.removeEventListener("pointermove", onPointerMove);
    doc.removeEventListener("load", schedule, true);
    win.removeEventListener("resize", schedule);
    observer?.disconnect();
  }

  /** Shown only while it holds a thread. Through the attribute: `hidden` is
   * an HTMLElement property and an SVG element does not have it, so setting
   * `svg.hidden` would change nothing on screen. Only a change is written,
   * because writing the same attribute again is still a mutation. */
  function show(on) {
    if (svg.hasAttribute("hidden") === on) svg.toggleAttribute("hidden", !on);
  }

  function clear() {
    if (svg.firstChild) svg.replaceChildren();
    show(false);
  }

  function scrubbing() {
    return doc.body.classList.contains("scrubbing") || Boolean(getBoard()?.root?.classList.contains("scrubbing"));
  }

  /**
   * Where on an origin its thread ends, as a rectangle (a point is a
   * rectangle with no size), or null when that place is not on screen.
   *
   * A group's thread ends at its label, because the label says which group
   * it is; the outline alone sits a few pixels from its members, so a thread
   * to it would be a stub. A connector's ends at the middle of its line,
   * because its ends already touch the notes it joins. Anything else ends at
   * its edge facing the note.
   */
  function anchor(origin, el, rect) {
    if (origin.kind === "group") {
      const label = el.querySelector('[class*="label"], [class*="title"]');
      return (label && visibleRect(label, win)) ?? rect;
    }
    if (origin.kind === "connector") {
      const line = typeof el.getTotalLength === "function" ? el : el.querySelector("path, line, polyline");
      const ctm = line?.getScreenCTM?.();
      if (!ctm || typeof line.getTotalLength !== "function") return rect;
      const p = line.getPointAtLength(line.getTotalLength() / 2).matrixTransform(ctm);
      const within = p.x >= rect.x - 1 && p.x <= rect.x + rect.w + 1 && p.y >= rect.y - 1 && p.y <= rect.y + rect.h + 1;
      return within ? { x: p.x, y: p.y, w: 0, h: 0 } : null;
    }
    return rect;
  }

  /** The first on-screen element for an origin, with where its thread ends. */
  function locate(origin, noteId, root) {
    for (const { scope, selector, svgOnly } of originSelectors(origin, noteId)) {
      const within = scope === "board" ? root : doc;
      if (!within) continue;
      for (const el of within.querySelectorAll(selector)) {
        if (svgOnly && el.namespaceURI !== SVG_NS) continue;
        if (scope === "page" && root?.contains(el)) continue;
        const seen = visibleRect(el, win);
        const rect = seen && anchor(origin, el, seen);
        if (rect) return { el, rect, scope };
      }
    }
    return null;
  }

  /** Whether the origin's dot can be seen, not merely lies inside its scroll
   * area: the rail's sticky tabs, a menu or a dialog may sit on top of it.
   * Only for page origins: on the board, notes sit on top of their own group
   * outline and connectors take no pointer events, so a hit test would say
   * every one of them is covered. */
  function uncovered(el, end) {
    const hit = doc.elementFromPoint(end.x - end.nx * 1.5, end.y - end.ny * 1.5);
    return Boolean(hit) && (hit === el || el.contains(hit));
  }

  function draw() {
    if (!selection.length || scrubbing()) { clear(); return; }
    const board = getBoard();
    const root = board?.root ?? doc.getElementById("board");
    const snapshot = board?.snapshot ?? getSnapshot();
    const links = readLinks(storage);
    const threads = [];
    for (const noteId of selection) {
      const noteEl = root?.querySelector(`.note[data-id=${q(noteId)}]`);
      const noteRect = noteEl && visibleRect(noteEl, win);
      if (!noteRect) continue;
      for (const origin of resolveOrigins(noteId, snapshot, links)) {
        const found = locate(origin, noteId, root);
        if (!found) continue;
        const ends = threadEnds(noteRect, found.rect);
        if (found.scope === "page" && !uncovered(found.el, ends.origin)) continue;
        threads.push({ noteId, origin, ends });
      }
    }
    if (!threads.length) { clear(); return; }
    const nodes = [];
    for (const { noteId, origin, ends } of threads) {
      const attrs = { "data-note": noteId, "data-origin": origin.kind };
      const path = doc.createElementNS(SVG_NS, "path");
      path.setAttribute("class", "thread");
      path.setAttribute("d", threadPath(ends.note, ends.origin));
      const dot = doc.createElementNS(SVG_NS, "circle");
      dot.setAttribute("class", "thread-dot");
      dot.setAttribute("cx", String(round(ends.origin.x)));
      dot.setAttribute("cy", String(round(ends.origin.y)));
      for (const [k, v] of Object.entries(attrs)) { path.setAttribute(k, v); dot.setAttribute(k, v); }
      nodes.push(path, dot);
    }
    svg.replaceChildren(...nodes);
    show(true);
  }

  return {
    /** The board's selection: note ids. An empty one clears and stops everything. */
    select(ids) {
      selection = Array.isArray(ids) ? ids.filter(id => typeof id === "string") : [];
      if (!selection.length) { frame.cancel(); detach(); clear(); return; }
      attach();
      frame.schedule();
    },
    schedule,
    get selection() { return [...selection]; },
    get listening() { return attached; },
    get pending() { return frame.pending; },
  };
}

// ------------------------------------------------------------------ registry

export function register(registerTool) {
  let threads = null, ctx = null;
  registerTool("threads", {
    mount(context) {
      ctx = context;
      const svg = document.getElementById("threads");
      if (!svg) return;
      threads = createThreads({ svg, getBoard: () => ctx?.board ?? null, getSnapshot: () => ctx?.app?.snapshot ?? null });
    },
    render() { threads?.schedule(); },
    onSelection(ids) { threads?.select(ids); },
    onZoom() { threads?.schedule(); },
  });
}
