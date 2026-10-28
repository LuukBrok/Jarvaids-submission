/**
 * Quote notes (DESIGN.md 1.2): a transcript line pulled onto the canvas as a
 * note whose text is the words, with a mono marker of the time they were said
 * that links back to the line.
 *
 * Owner: the phase 3 quote notes agent (DESIGN.md 1.5), with css/quote.css.
 *
 * How it fits together:
 *
 *   The rail's transcript rows carry a Quote button that dispatches
 *   `jv:quote` on the document with {segmentId, text, speakerName,
 *   speakerActorId, createdAt}. This module listens for it and sends the
 *   words as a typed note (`source.text`), so a quote is reviewed like any
 *   person's note. The text ends in " · 14:02", the time it was said, so the
 *   link survives as text on a device that never saw the quote made.
 *
 *   The link from note to line is kept on this device in localStorage under
 *   `jv.quotes.links`, a JSON object of proposal id to
 *   {segmentId, time, speakerActorId}, behind the flag `jv.flags.quoteLinks`
 *   (on unless set to "0", "false" or "off"). The server has no reference
 *   kind for a transcript segment yet, which is the open decision in
 *   docs/proposal-organise-step.md; when it has one, this store goes.
 *
 *   An accepted proposal becomes an item carrying `data.proposal_id`, so an
 *   item is linked when the proposal it came from is. On a device without
 *   the stored link, a note whose text ends in the marker is linked to the
 *   transcript line with exactly those words said at exactly that minute, so
 *   another screen in the room draws the same quote.
 *
 *   After the board draws, every linked note gets its speaker's People
 *   colour as its fill, the class `note-quote`, and a `.quote-marker` button
 *   showing the time. Pressing it opens the Transcript, scrolls the line into
 *   view and highlights it (`quoted-highlight`) for two seconds. The marker
 *   at the end of the note's own text is wrapped in `.quote-time` and hidden,
 *   so the time reads as a marker, not as part of the sentence; the text's
 *   full textContent is unchanged.
 */
import { memberName } from "../board.mjs";
import { sentenceRows } from "../transcript-sentences.mjs";

export const LINKS_KEY = "jv.quotes.links";
export const FLAG_KEY = "jv.flags.quoteLinks";
export const HIGHLIGHT_MS = 2000;
/** A device keeps the newest links only. Each is about 120 bytes, so this
 * is some 60 KB, far under any browser's quota; a guess, tested by filling
 * the store in quote-unit.mjs. */
export const MAX_LINKS = 500;
export const QUOTED = "Quoted onto the canvas, waiting for review.";
export const SESSION_ONLY = "Quote links are kept for this session only";
/** --person-1 to --person-10 in tokens.css; the eleventh person wraps to 1. */
export const PEOPLE = 10;
/** The People colours after the fifth are -deep accents, which carry
 * --paper text, not --ink (DESIGN.md 2.2). */
const FULL_PEOPLE = 5;
const DOT = "·";
const MARKER = new RegExp(` ${DOT} (\\d{2}:\\d{2})$`);

// --------------------------------------------------------------- pure parts

/** HH:MM, 24 hour, in this device's time zone. Accepts seconds (the server's
 * `created_at`) or milliseconds. Null when there is no usable time. */
export function quoteTime(createdAt) {
  const n = Number(createdAt);
  if (createdAt == null || !Number.isFinite(n) || n <= 0) return null;
  const d = new Date(n > 1e11 ? n : n * 1000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** The words as one line: a quote is a sentence, not a layout. */
export function quoteWords(text) {
  return String(text ?? "").replace(/\s+/g, " ").trim();
}

/** The note's text: the words, then " · 14:02". Without a time, the words. */
export function quoteText(text, createdAt) {
  const words = quoteWords(text), time = quoteTime(createdAt);
  return time ? `${words} ${DOT} ${time}` : words;
}

/** The trailing marker of a note's text, or null when it has none. */
export function splitMarker(text) {
  const value = String(text ?? "");
  const match = MARKER.exec(value);
  if (!match) return null;
  return { words: value.slice(0, match.index), marker: match[0], time: match[1] };
}

/** 1 to 10: the speaker's place in the session's members, wrapping after
 * ten. 0 when the speaker is not a member, so no colour is claimed. */
export function personIndex(members, actorId) {
  const i = (members ?? []).findIndex(m => m.id === actorId);
  return i < 0 ? 0 : (i % PEOPLE) + 1;
}

/** "full" for the five accents, which carry --ink text; "deep" for the
 * five -deep accents, which carry --paper text. */
export function personTone(n) {
  return n > FULL_PEOPLE ? "deep" : "full";
}

function validLink(value) {
  return value && typeof value === "object" && typeof value.segmentId === "string" && value.segmentId
    ? { segmentId: value.segmentId,
        time: Number.isFinite(value.time) ? value.time : null,
        speakerActorId: typeof value.speakerActorId === "string" ? value.speakerActorId : null }
    : null;
}

/** Parsed links, dropping anything that is not one. A damaged entry costs
 * that one quote its link, never the others. */
export function parseLinks(raw) {
  let value;
  try { value = JSON.parse(raw); } catch { return {}; }
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const out = {};
  for (const [id, link] of Object.entries(value)) { const ok = validLink(link); if (ok) out[id] = ok; }
  return out;
}

/** The link store. Writes go to `storage` (localStorage in the page) and to
 * memory; if storage is missing or throws, it carries on in memory and calls
 * onFallback once, so the person can be told the links will not outlive the
 * page. Writing merges what another tab stored meanwhile, so two tabs on one
 * device do not drop each other's links. */
export function createLinkStore(storage, { onFallback = () => {}, max = MAX_LINKS } = {}) {
  const links = new Map();
  let persistent = Boolean(storage), told = false;
  const fallback = () => {
    persistent = false;
    if (!told) { told = true; onFallback(); }
  };
  const read = () => parseLinks(storage.getItem(LINKS_KEY) ?? "{}");
  if (!storage) fallback();
  else {
    try { for (const [id, link] of Object.entries(read())) links.set(id, link); }
    catch { fallback(); }
  }
  return {
    get persistent() { return persistent; },
    get(id) { return id ? links.get(id) ?? null : null; },
    set(id, link) {
      const ok = validLink(link);
      if (!id || !ok) return false;
      if (persistent) {
        try { for (const [other, value] of Object.entries(read())) if (!links.has(other)) links.set(other, value); }
        catch { fallback(); }
      }
      links.delete(id);
      links.set(id, ok);
      while (links.size > max) links.delete(links.keys().next().value);
      if (persistent) {
        try { storage.setItem(LINKS_KEY, JSON.stringify(Object.fromEntries(links))); }
        catch { fallback(); }
      }
      return true;
    },
    get size() { return links.size; },
  };
}

/** The flag: on unless it says otherwise. Unreadable storage means on. */
export function flagOn(storage) {
  try { return !["0", "false", "off"].includes(String(storage?.getItem(FLAG_KEY) ?? "").trim().toLowerCase()); }
  catch { return true; }
}

/** The stored link of a proposal, or of the item its acceptance made. */
export function storedLink(store, record) {
  if (!record) return null;
  return store.get(record.id) ?? (record.kind === "item" ? store.get(record.data?.proposal_id) : null);
}

/** The transcript lines as the rail shows them: final segments in time
 * order, joined into sentences, each named by its first segment's id. */
function lines(snapshot) {
  const segments = (snapshot?.records ?? []).filter(r => r.kind === "transcript_segment" &&
    r.data.status === "final" && r.data.text?.trim())
    .sort((a, b) => (a.data.created_at ?? 0) - (b.data.created_at ?? 0));
  return sentenceRows(segments);
}

/** The link a note's own text implies: the line with exactly these words,
 * said at exactly this minute. Null unless there is exactly one, because a
 * guess pointing at the wrong line is worse than no pointer. */
export function textLink(snapshot, record, cache = null) {
  const parts = splitMarker(record?.data?.text);
  if (!parts) return null;
  const words = quoteWords(parts.words);
  const rows = cache ?? lines(snapshot);
  const hits = rows.filter(row => quoteWords(row.data.display_text ?? row.data.text) === words &&
    quoteTime(row.data.created_at) === parts.time);
  if (hits.length !== 1) return null;
  const d = hits[0].data;
  return { segmentId: hits[0].id, time: d.created_at ?? null, speakerActorId: d.speaker_actor_id ?? null };
}

/** Who said it, named as the transcript names them. */
export function speakerLabel(snapshot, link) {
  const d = (snapshot?.records ?? []).find(r => r.id === link.segmentId)?.data;
  if (d?.attribution === "voice_identified" && d.speaker_name) return d.speaker_name;
  if (d?.attribution === "unidentified") return "Unknown speaker";
  return memberName(snapshot, link.speakerActorId);
}

// ------------------------------------------------------------- the tool

export function register(registerTool) {
  let ctx = null, store = null, enabled = true, tellSessionOnly = false;
  const inFlight = new Set();
  let lit = null;          // {segmentId, timer}: the line highlighted now
  let focusKey = null;     // the marker that had focus before the board redrew

  /** Decorates every linked note the board has drawn. Idempotent: a note
   * already decorated since the board last drew it is left alone. */
  function decorate(snapshot) {
    const world = ctx?.board?.world;
    if (!enabled || !snapshot || !world) return;
    const byId = new Map(snapshot.records.map(r => [r.id, r]));
    let cache = null;
    for (const el of world.querySelectorAll(".note[data-id]")) {
      if (el.classList.contains("note-quote")) continue;
      const record = byId.get(el.dataset.id);
      if (!record) continue;
      let link = storedLink(store, record);
      if (!link && splitMarker(record.data?.text)) link = textLink(snapshot, record, cache ??= lines(snapshot));
      if (link) dress(el, record, link, snapshot);
    }
    if (focusKey && (!document.activeElement || document.activeElement === document.body)) {
      world.querySelector(`.quote-marker[data-focus-key="${focusKey}"]`)?.focus({ preventScroll: true });
    }
  }

  function dress(el, record, link, snapshot) {
    const n = personIndex(snapshot.members, link.speakerActorId);
    if (n) {
      el.style.setProperty("--note-fill", `var(--person-${n})`);
      el.dataset.quoteTone = personTone(n);
    } else {
      // Nobody known said it (an unknown or unmatched voice): no person's
      // colour is claimed, and the note takes the typed note's yellow, so a
      // quote still waiting for review never shows the paper "not yet
      // reviewed" look that the quote's own marker would contradict.
      el.style.setProperty("--note-fill", "var(--note-accepted-fill)");
      el.dataset.quoteTone = "full";
    }
    el.classList.add("note-quote");
    // For the provenance threads: the line this note points at.
    el.dataset.quoteSegment = link.segmentId;
    const who = speakerLabel(snapshot, link);
    const kind = el.querySelector(".kind");
    // Colour is not the only sign of who said it: the label names them.
    if (kind) kind.textContent = `Quote · ${who}`;

    const text = el.querySelector(".text");
    const parts = text ? splitMarker(text.textContent) : null;
    if (parts) {
      const span = document.createElement("span");
      span.className = "quote-time";
      span.textContent = parts.marker;
      text.textContent = parts.words;
      text.append(span);
    }

    const time = quoteTime(link.time) ?? parts?.time ?? null;
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "quote-marker";
    marker.textContent = time ?? "Transcript";
    marker.setAttribute("aria-label", time ? `Said at ${time} by ${who}. Show the line in the transcript`
      : `Said by ${who}. Show the line in the transcript`);
    marker.dataset.focusKey = `quote-${record.id}`;
    marker.addEventListener("click", () => showLine(link.segmentId));
    (el.querySelector(".note-head") ?? el).append(marker);
  }

  function showLine(segmentId) {
    ctx.rail("transcript");
    const row = document.getElementById(`seg-${segmentId}`);
    if (!row) {
      ctx.attention("That line is not in the transcript on this screen.", "note");
      return;
    }
    if (lit) { clearTimeout(lit.timer); document.getElementById(`seg-${lit.segmentId}`)?.classList.remove("quoted-highlight"); }
    row.classList.add("quoted-highlight");
    const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const already = inView(row);
    row.scrollIntoView({ block: "center", behavior: still ? "auto" : "smooth" });
    const current = lit = { segmentId, timer: 0 };
    // The two seconds start when the line is where the eye can find it: at
    // once if it was in view, otherwise when the scroll ends (or after a
    // second, for a browser that never says).
    const begin = () => {
      document.removeEventListener("scrollend", begin, true);
      if (lit !== current || current.timer) return;
      current.timer = setTimeout(() => {
        document.getElementById(`seg-${segmentId}`)?.classList.remove("quoted-highlight");
        if (lit === current) lit = null;
      }, HIGHLIGHT_MS);
    };
    if (already || still) { begin(); return; }
    document.addEventListener("scrollend", begin, true);
    setTimeout(begin, 1000);
  }

  /** Inside the window and every scrolling box around it. */
  function inView(el) {
    const r = el.getBoundingClientRect();
    if (r.top < 0 || r.bottom > window.innerHeight) return false;
    for (let box = el.parentElement; box; box = box.parentElement) {
      if (!/(auto|scroll)/.test(getComputedStyle(box).overflowY)) continue;
      const c = box.getBoundingClientRect();
      if (r.top < c.top || r.bottom > c.bottom) return false;
    }
    return true;
  }

  /** The transcript is redrawn from the snapshot on every render, so a
   * highlight still running is put back on the new row. */
  function relight() {
    if (lit) document.getElementById(`seg-${lit.segmentId}`)?.classList.add("quoted-highlight");
  }

  async function quote(detail) {
    const words = quoteWords(detail?.text);
    const segmentId = detail?.segmentId ? String(detail.segmentId) : "";
    // One at a time per line, so a double press does not quote it twice.
    if (!words || !segmentId || inFlight.has(segmentId)) return;
    inFlight.add(segmentId);
    try {
      let result;
      try { result = await ctx.send("source.text", { text: quoteText(words, detail.createdAt) }); }
      catch { return; }   // the banner already says why; nothing was added
      const proposal = result?.proposal;
      if (enabled && proposal?.id) {
        const time = Number(detail.createdAt);
        store.set(proposal.id, { segmentId, time: Number.isFinite(time) ? time : null,
          speakerActorId: detail.speakerActorId ? String(detail.speakerActorId) : null });
        decorate(ctx.app.snapshot);
      }
      // One banner at a time (app.mjs), so the session-only notice rides on
      // the first quote that needs it rather than being replaced by it.
      const notice = enabled && tellSessionOnly ? ` ${SESSION_ONLY}.` : "";
      tellSessionOnly = false;
      ctx.attention((ctx.app.snapshot?.session?.automatic_workspace ? "Quoted onto the canvas." : QUOTED) + notice, "note");
    } finally {
      inFlight.delete(segmentId);
    }
  }

  registerTool("quote", {
    mount(context) {
      ctx = context;
      let storage = null;
      try { storage = window.localStorage; } catch { storage = null; }
      enabled = flagOn(storage);
      store = createLinkStore(enabled ? storage : null, { onFallback: () => { tellSessionOnly = enabled; } });
      document.addEventListener("jv:quote", event => { quote(event.detail).catch(error => console.error(error)); });
      // A row redrawn while a highlight runs, or given its id after it was
      // put in, is lit again; the render hook alone would miss the second.
      const transcript = document.getElementById("transcript");
      if (transcript) new MutationObserver(relight).observe(transcript,
        { childList: true, subtree: true, attributes: true, attributeFilter: ["id"] });
      const world = ctx.board?.world;
      if (!world) return;
      // The board also redraws on its own (details opened, a crop loaded, a
      // drag settled), without a render that reaches the tools.
      new MutationObserver(() => decorate(ctx.app.snapshot)).observe(world, { childList: true });
      world.addEventListener("focusin", event => {
        if (event.target.matches?.(".quote-marker")) focusKey = event.target.dataset.focusKey;
      });
      // Focus that left a marker still on the page went somewhere on
      // purpose; focus lost because the board took the marker away is put
      // back on the new one by decorate().
      world.addEventListener("focusout", event => {
        const left = event.target;
        if (!left.matches?.(".quote-marker")) return;
        if (event.relatedTarget) { focusKey = null; return; }
        setTimeout(() => { if (left.isConnected && focusKey === left.dataset.focusKey) focusKey = null; }, 0);
      });
    },
    render(_ctx, snapshot) {
      decorate(snapshot);
      relight();
    },
  });
}
