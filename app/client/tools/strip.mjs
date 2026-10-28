/**
 * The session strip: the session's moments along the bottom of the canvas,
 * and scrubbing through them (DESIGN.md 1.1, move 3, and 1.2).
 *
 * Owner: the phase 3 session strip agent (DESIGN.md 1.5), with
 * css/strip.css and the <!-- region: strip --> block in index.html.
 *
 * One mark per moment, on a time axis from the session's first moment to now:
 *
 *   photograph        a source record of type image          small square
 *   accept            an accepted content item               filled circle, the note's colour
 *   voice command     a recognised command on a segment      periwinkle bar
 *   quote             a note in the quote links              short line
 *
 * Every time is the record's own `data.created_at` in seconds. An accepted
 * item is created at the moment of acceptance (service.py, proposal.review),
 * so its `created_at` is when it was accepted.
 *
 * Scrubbing (a pointer drag, or the keys while the strip has focus) sets a
 * moment. While one is set, everything on the canvas made after it is marked
 * with the class `after-moment`: notes accepted later and canvas items made
 * later fade to 20 percent, and proposals made later carry
 * `after-moment-proposal` as well and are not shown, because at that moment
 * they did not exist. Positions stay current: the server keeps no position
 * history (DESIGN.md 1.4). Releasing the pointer, Escape or End returns to
 * now and removes both classes everywhere.
 *
 * Persists nothing. Reads one localStorage key, `jv.quotes.links` (written by
 * the quote tool): note id to {segmentId, time}.
 *
 * The pure parts (moments, the axis, what is after a moment, the words) are
 * exported for tests/strip-unit.mjs; the DOM part is createStrip().
 */
import { shortText } from "../canvas-objects.mjs";
import { commandFeedback } from "../../server/voice-command-feedback.mjs";

export const QUOTE_LINKS_KEY = "jv.quotes.links";
/** Classes this tool adds to other regions' elements, and removes again. */
export const AFTER = "after-moment";
export const AFTER_PROPOSAL = "after-moment-proposal";
/** The shortest axis, in seconds, so a session with one moment still has a
 * line to scrub along instead of a single point. */
export const MIN_SPAN = 60;
/** A pointer within this many pixels of a mark lands on that moment, so a
 * person can hit an 8px mark with a mouse. */
const SNAP_PX = 6;
/** A resting pointer this close to a mark's centre shows that moment's words. */
const HOVER_PX = 10;
const KINDS = ["photo", "accept", "command", "quote"];
const LANE_WORDS = { photo: "photo", accept: "accept", command: "command", quote: "quote" };

const finite = n => typeof n === "number" && Number.isFinite(n);

// ------------------------------------------------------------- pure parts

/** The quote links, or {} when absent or unreadable. `storage` is anything
 * with getItem; a private window or blocked storage throws, which reads as
 * no links. */
export function readQuoteLinks(storage) {
  try {
    const raw = storage?.getItem(QUOTE_LINKS_KEY);
    const links = raw ? JSON.parse(raw) : {};
    return links && typeof links === "object" && !Array.isArray(links) ? links : {};
  } catch {
    return {};
  }
}

/** The command's own words, taken from the transcript's feedback sentence so
 * there is one list of command names (voice-command-feedback.mjs). */
export function commandWords(heard) {
  const match = /^Provisional command: (.+) requested\./.exec(commandFeedback(heard));
  return match ? match[1] : String(heard?.intent ?? "command");
}

/** Every moment in a snapshot, oldest first. Ties keep snapshot order.
 *  {key, kind, id, time, text?, words?} */
export function momentsFrom(snapshot, links = {}) {
  const records = snapshot?.records ?? [];
  const out = [];
  const add = (kind, id, time, extra = {}) => { if (finite(time)) out.push({ key: `${kind}:${id}`, kind, id, time, ...extra }); };
  for (const r of records) {
    const d = r.data ?? {};
    if (r.kind === "source" && d.type === "image") add("photo", r.id, d.created_at);
    else if (r.kind === "item" && d.item_kind === "content" && d.status === "accepted") add("accept", r.id, d.created_at, { text: d.text ?? "" });
    // A synthetic segment never shows a command in the transcript
    // (transcript.mjs), so it never makes a moment here either.
    else if (r.kind === "transcript_segment" && d.voice_command?.status === "recognised" && !d.provenance?.synthetic) {
      add("command", r.id, d.created_at, { words: commandWords(d.voice_command) });
    }
  }
  for (const [id, link] of Object.entries(links)) {
    // The note may be the typed proposal or the item it became when accepted.
    const r = records.find(x => x.id === id) ?? records.find(x => x.data?.proposal_id === id);
    let time = r?.data?.created_at;
    if (!finite(time) && finite(link?.time)) time = link.time > 1e11 ? link.time / 1000 : link.time;
    add("quote", id, time);
  }
  return out.map((m, i) => [m, i]).sort((a, b) => a[0].time - b[0].time || a[1] - b[1]).map(([m]) => m);
}

/** The axis: from the first moment to now, at least MIN_SPAN long. Now never
 * comes before the newest moment, so a clock behind the server's still draws
 * every mark. */
export function axisFrom(moments, now) {
  const last = moments.length ? moments[moments.length - 1].time : now;
  const end = Math.max(now, last);
  const first = moments.length ? moments[0].time : end;
  return { start: Math.min(first, end - MIN_SPAN), end };
}

/** Time to a fraction along the axis, clamped to 0..1, and back. */
export function fractionOf(axis, time) {
  const span = axis.end - axis.start;
  return span > 0 ? Math.min(1, Math.max(0, (time - axis.start) / span)) : 0;
}
export function timeAt(axis, fraction) {
  return axis.start + Math.min(1, Math.max(0, fraction)) * (axis.end - axis.start);
}

/** What was made after a moment. An item made after it (an accepted note is
 * made when it is accepted) fades; a proposal made after it did not exist,
 * so it goes. A record made at exactly the moment counts as already there. */
export function afterMoment(snapshot, time) {
  const faded = new Set(), gone = new Set();
  if (!finite(time)) return { faded, gone };
  for (const r of snapshot?.records ?? []) {
    const at = r.data?.created_at;
    if (!finite(at) || at <= time) continue;
    if (r.kind === "proposal") gone.add(r.id);
    else if (r.kind === "item") faded.add(r.id);
  }
  return { faded, gone };
}

/** The words for one moment: "Photograph · 14:02", "Accepted · Too many
 * fields · 14:05", "Command · summary · 14:07", "Quote · 14:09". The note's
 * words are cut at `max` characters for the label over the mark; the
 * slider's value text passes Infinity, so a screen reader hears them whole. */
export function momentLabel(moment, clock, max = 32) {
  const at = clock(moment.time);
  switch (moment.kind) {
    case "photo": return `Photograph · ${at}`;
    case "accept": return moment.text?.trim() ? `Accepted · ${shortText(moment.text, max)} · ${at}` : `Accepted · ${at}`;
    case "command": return `Command · ${moment.words} · ${at}`;
    case "quote": return `Quote · ${at}`;
    default: return at;
  }
}

/** One key press along the moments. `at` is the current place: null for
 * now, or {time, index} where index is the moment stood on (null when a
 * pointer left it between moments). Returns the new place; null is now.
 * dir is -1 (back), +1 (forward), "first" or "now". */
export function step(moments, at, dir) {
  if (dir === "now" || !moments.length) return null;
  if (dir === "first") return { time: moments[0].time, index: 0 };
  let index;
  if (at == null) index = dir < 0 ? moments.length - 1 : moments.length;
  else if (at.index != null) index = at.index + dir;
  else if (dir < 0) index = moments.findLastIndex(m => m.time < at.time);
  else index = moments.findIndex(m => m.time > at.time);
  if (dir < 0 && index < 0) index = 0;
  if (index < 0 || index >= moments.length) return null;
  return { time: moments[index].time, index };
}

// --------------------------------------------------------------- the strip

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

/** The DOM half: builds the strip inside #session-strip at mount, redraws
 * its marks on every render and reapplies the moment's classes, because the
 * board rebuilds its elements on every render. */
export function createStrip() {
  let ctx = null, root = null, axisEl = null, rail = null, lanes = null, tip = null, cursor = null, cursorTime = null;
  let startEl = null, endEl = null, toggle = null, empty = null;
  let snapshot = null, moments = [], axis = { start: 0, end: 0 };
  let at = null;          // null is now; else {time, index}
  let scrubbing = false;  // a pointer is down on the strip
  let open = false;       // pinned open by the quiet control
  let observer = null;

  const clock = seconds => ctx.clock(seconds);
  const now = () => Date.now() / 1000;

  function build() {
    root.classList.add("strip");
    root.textContent = "";
    root.dataset.open = "false";
    const future = el("div", "strip-future");
    future.setAttribute("aria-hidden", "true");
    lanes = el("div", "strip-lanes t-mono");
    lanes.setAttribute("aria-hidden", "true");
    for (const kind of KINDS) lanes.append(el("span", `strip-lane-word strip-lane-${kind}`, LANE_WORDS[kind]));
    startEl = el("span", "strip-end strip-start t-mono");
    endEl = el("span", "strip-end strip-now t-mono");

    axisEl = el("div", "strip-axis");
    axisEl.id = "session-strip-axis";
    axisEl.tabIndex = 0;
    axisEl.setAttribute("role", "slider");
    axisEl.setAttribute("aria-label", "Session time");
    axisEl.setAttribute("aria-orientation", "horizontal");
    const help = el("span", "visually-hidden",
      "Arrow keys step through the session's photographs, accepts, commands and quotes; Home goes to the first, End and Escape return to now. Notes accepted later fade and later proposals are hidden.");
    help.id = "session-strip-help";
    axisEl.setAttribute("aria-describedby", help.id);
    rail = el("div", "strip-rail");
    empty = el("span", "strip-empty t-small", "No moments yet");
    axisEl.append(rail, empty);

    const timeRow = el("div", "strip-timerow");
    timeRow.setAttribute("aria-hidden", "true");
    cursor = el("div", "strip-cursor");
    cursor.setAttribute("aria-hidden", "true");
    cursor.hidden = true;
    cursorTime = el("span", "strip-cursor-time t-mono");
    cursor.append(el("span", "strip-cursor-line"), cursorTime);
    tip = el("div", "strip-tip t-small");
    tip.setAttribute("aria-hidden", "true");
    tip.hidden = true;

    toggle = el("button", "btn btn-quiet btn-sm strip-toggle");
    toggle.type = "button";
    toggle.setAttribute("aria-controls", root.id);
    toggle.innerHTML = '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M5 12.5 10 7.5 15 12.5"/></svg>';
    setOpen(false);

    root.append(future, lanes, startEl, axisEl, endEl, toggle, timeRow, cursor, tip, help);
  }

  function setOpen(on) {
    open = on;
    root.dataset.open = String(on);
    toggle.setAttribute("aria-expanded", String(on));
    toggle.setAttribute("aria-label", on ? "Show the session strip smaller" : "Show the session strip larger");
  }

  // ---------------------------------------------------------------- drawing

  function draw() {
    const links = readQuoteLinks(globalThis.localStorage);
    moments = momentsFrom(snapshot, links);
    axis = axisFrom(moments, now());
    // A place stood on by the keys follows its moment if the list changed.
    if (at?.index != null) {
      const key = at.key;
      const index = moments.findIndex(m => m.key === key);
      at = index >= 0 ? { time: moments[index].time, index, key } : { time: at.time, index: null };
    }
    rail.textContent = "";
    for (const m of moments) {
      const mark = el("span", `strip-mark strip-mark-${m.kind}`);
      // data-key, not data-id: other regions find records by [data-id].
      mark.dataset.key = m.key;
      mark.style.left = `${fractionOf(axis, m.time) * 100}%`;
      if (m.kind === "accept") {
        // The note's own colour as the board draws it; yellow when the note
        // is not drawn (list view, or another region owns it).
        const note = document.querySelector(`.note[data-id="${CSS.escape(m.id)}"]`);
        const fill = note ? getComputedStyle(note).getPropertyValue("--note-fill").trim() : "";
        if (fill) mark.style.setProperty("--mark-fill", fill);
      }
      rail.append(mark);
    }
    root.dataset.empty = String(moments.length === 0);
    startEl.textContent = moments.length ? clock(axis.start) : "";
    endEl.textContent = clock(axis.end);
    axisEl.setAttribute("aria-valuemin", String(Math.floor(axis.start)));
    axisEl.setAttribute("aria-valuemax", String(Math.ceil(axis.end)));
    place();
  }

  /** The cursor, the paper to its right, the slider's value and the label. */
  function place() {
    const value = at ? at.time : axis.end;
    axisEl.setAttribute("aria-valuenow", String(Math.round(value)));
    const on = at?.index != null ? moments[at.index] : null;
    axisEl.setAttribute("aria-valuetext", !at ? `Now, ${clock(axis.end)}` : on ? momentLabel(on, clock, Infinity) : clock(at.time));
    root.classList.toggle("strip-scrubbing", Boolean(at));
    cursor.hidden = !at;
    if (at) {
      const x = xOf(at.time);
      root.style.setProperty("--cursor-x", `${x}px`);
      cursorTime.textContent = clock(at.time);
      if (on) showTip(on); else hideTip();
    } else {
      root.style.removeProperty("--cursor-x");
      if (!hovered) hideTip();
    }
    apply();
  }

  /** x of a time, in pixels from the strip's left edge. */
  function xOf(time) {
    const r = rail.getBoundingClientRect(), s = root.getBoundingClientRect();
    return r.left - s.left + fractionOf(axis, time) * r.width;
  }

  let hovered = null;
  function showTip(moment) {
    tip.textContent = momentLabel(moment, clock);
    tip.hidden = false;
    // Centred over its mark, but never past the strip's edges, so a mark at
    // either end cannot make the page scroll sideways.
    const width = root.clientWidth, w = tip.offsetWidth;
    const left = Math.min(Math.max(0, xOf(moment.time) - w / 2), Math.max(0, width - w));
    tip.style.left = `${left}px`;
  }
  function hideTip() { tip.hidden = true; }

  // ------------------------------------------------- the classes on the canvas

  /** Marks what was made after the moment, everywhere it is drawn: the
   * board, the parked margin, and any note elsewhere except the review
   * rail. Clears it at now. */
  function apply() {
    // The page says a moment is set, so other tools can stand down: the
    // provenance threads draw nothing while the body has `scrubbing`,
    // because they would point at the present from a picture of the past.
    document.body.classList.toggle("scrubbing", Boolean(at));
    if (!at) {
      for (const node of document.querySelectorAll(`.${AFTER}, .${AFTER_PROPOSAL}`)) node.classList.remove(AFTER, AFTER_PROPOSAL);
      watch(false);
      return;
    }
    const { faded, gone } = afterMoment(snapshot, at.time);
    const targets = new Set(document.querySelectorAll("#board [data-id], #parked [data-id], .note[data-id]"));
    for (const node of document.querySelectorAll(`.${AFTER}`)) targets.add(node);
    for (const node of targets) {
      // Review is present tense: the rail's cards are never faded.
      if (node.closest(".ws-rail")) continue;
      const id = node.dataset?.id ?? node.getAttribute("data-id");
      const later = faded.has(id) || gone.has(id);
      node.classList.toggle(AFTER, later);
      node.classList.toggle(AFTER_PROPOSAL, gone.has(id));
    }
    watch(true);
  }

  /** The board can redraw itself between renders (details, a crop arriving,
   * the end of a drag), which drops the classes. While a moment is set, a
   * redraw puts them back. */
  function watch(on) {
    if (!on) { observer?.disconnect(); observer = null; return; }
    if (observer || typeof MutationObserver === "undefined") return;
    let queued = false;
    observer = new MutationObserver(() => {
      if (queued) return;
      queued = true;
      queueMicrotask(() => { queued = false; if (at) apply(); });
    });
    for (const id of ["board", "parked"]) {
      const node = document.getElementById(id);
      if (node) observer.observe(node, { childList: true, subtree: true });
    }
  }

  // ------------------------------------------------------------- scrubbing

  function setPlace(next) {
    at = next ? { ...next, key: next.index != null ? moments[next.index]?.key : undefined } : null;
    place();
  }

  /** A pointer's place: the time under it, or the moment whose mark is
   * within SNAP_PX of it. */
  function placeAtPointer(clientX) {
    const r = rail.getBoundingClientRect();
    const time = timeAt(axis, r.width ? (clientX - r.left) / r.width : 0);
    let best = null, bestDx = SNAP_PX + 1;
    moments.forEach((m, index) => {
      const dx = Math.abs(r.left + fractionOf(axis, m.time) * r.width - clientX);
      if (dx < bestDx) { best = index; bestDx = dx; }
    });
    setPlace(best != null ? { time: moments[best].time, index: best } : { time, index: null });
  }

  /** The moment whose mark is nearest the pointer, within HOVER_PX of it.
   * Nearest rather than topmost, because two marks a few seconds apart
   * overlap and the one drawn last would otherwise always win. */
  function nearestMark(x, y) {
    let best = null, bestD = HOVER_PX;
    for (const mark of rail.children) {
      const r = mark.getBoundingClientRect();
      const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
      if (d <= bestD) { bestD = d; best = mark.dataset.key; }
    }
    return best ? moments.find(m => m.key === best) ?? null : null;
  }

  function wire() {
    root.addEventListener("pointerdown", event => {
      if (event.button !== 0 || event.target.closest(".strip-toggle")) return;
      // A press on the axis focuses it the browser's own way, so the focus
      // ring stays a keyboard thing. A press in a gutter would blur it
      // instead, so there the focus is moved by hand.
      if (!axisEl.contains(event.target)) {
        event.preventDefault();
        axisEl.focus({ preventScroll: true });
      }
      scrubbing = true;
      root.setPointerCapture?.(event.pointerId);
      placeAtPointer(event.clientX);
    });
    root.addEventListener("pointermove", event => {
      if (scrubbing) { placeAtPointer(event.clientX); return; }
      const moment = nearestMark(event.clientX, event.clientY);
      hovered = moment;
      if (moment) showTip(moment);
      else if (!(at?.index != null)) hideTip();
    });
    root.addEventListener("pointerleave", () => {
      hovered = null;
      if (!(at?.index != null)) hideTip();
    });
    const release = () => {
      if (!scrubbing) return;
      scrubbing = false;
      setPlace(null);
    };
    root.addEventListener("pointerup", release);
    root.addEventListener("pointercancel", release);
    root.addEventListener("lostpointercapture", release);

    axisEl.addEventListener("keydown", event => {
      const keys = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, Home: "first", End: "now" };
      if (event.key === "Escape") {
        if (!at) return;            // nothing to undo; let Escape reach the page
        event.preventDefault();
        setPlace(null);
        return;
      }
      if (!(event.key in keys)) return;
      event.preventDefault();
      setPlace(step(moments, at, keys[event.key]));
    });
    axisEl.addEventListener("focus", () => root.classList.add("strip-focused"));
    axisEl.addEventListener("blur", () => {
      root.classList.remove("strip-focused");
      // Leaving the strip is leaving the moment: the canvas is never left
      // showing the past while a person works on it.
      if (!scrubbing && at) setPlace(null);
    });
    toggle.addEventListener("click", () => { setOpen(!open); if (at) place(); });
  }

  return {
    mount(context) {
      ctx = context;
      root = ctx.$("session-strip");
      if (!root) return;
      build();
      wire();
    },
    render(context, snap) {
      ctx = context;
      if (!root) return;
      snapshot = snap;
      // Only with the canvas: scrubbing shows the wall at a moment, and the
      // list and the Calendar view draw no wall to show.
      const visible = ctx.app?.screen === "workspace" && ctx.app?.view === "canvas" && Boolean(snap?.session);
      ctx.show(root, visible);
      if (!visible) { at = null; scrubbing = false; apply(); return; }
      draw();
    },
    /** For tests: the current place, null for now. */
    get place() { return at; },
  };
}

export function register(registerTool) {
  registerTool("strip", createStrip());
}
