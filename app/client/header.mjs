/**
 * The header and the banners (DESIGN.md 1.3, 1.5): the session title, the one
 * state chip, the participant line, and the capture banner inside the
 * header's bottom edge.
 *
 * app.mjs's render() sets the words it always set (`#state-word`, the
 * members button, which banner part shows); this tool's render runs after it
 * and wins where both touch an element. Two things change without a render,
 * so the tool also watches them: `#listen-status` (app.mjs shows it when this
 * device's microphone starts and hides it when it stops) and the agreement
 * screen's `hidden` attribute.
 *
 * The chip says only what is true: "Listening" with the bars and a timer
 * only while this device's microphone is on; otherwise the session's state.
 * "Session open" is never "Listening".
 *
 * The keep-alive countdown is an estimate made from what this screen saw.
 * Capture's lease runs out five minutes after the last renewal (activation
 * or a heartbeat). The heartbeat goes every 30 seconds once enabled, and the
 * client is not told when one lands, so the tool counts beats from the
 * moment it saw the heartbeat come on and keeps the last whole beat. That
 * errs early, never late: a countdown that reached zero while capture still
 * ran would teach the room to ignore it. When this screen saw neither an
 * activation nor a heartbeat, it says "within 5 minutes" instead of a number.
 *
 * The Jarvaids menu makes the commands visible and startable without
 * speaking. Each executed item sends the addressed words a person would say
 * ("Hey Jarvaids, make a to do list.") as a typed input through `send`
 * (source.text), the composer's route, so the server, the record and the
 * transcript treat it exactly as a typed command; no new operation exists
 * for it. The four commands that are recognised but not carried out are
 * listed as unavailable, in those words. "What you can say" opens a sheet of
 * example phrases. The collecting chip beside the state chip says when a
 * list or the calendar is collecting or a poll is open, and shows that card.
 *
 * The pure parts are exported for tests/header-unit.mjs.
 */
import { agreed, names, waitingFor } from "./people.mjs";

export const LEASE_MS = 5 * 60 * 1000;
export const HEARTBEAT_MS = 30 * 1000;
export const URGENT_MS = 60 * 1000;

// ------------------------------------------------------------------ the chip

const CHIP = {
  listening: { word: "Listening", className: "chip-listening" },
  active: { word: "Session open", className: "chip-open" },
  paused: { word: "Paused", className: "chip-paused" },
  closed: { word: "Ended", className: "chip-ended" },
  draft: { word: "Not started", className: "chip-idle" },
};

/** The chip for a session state and whether this device is listening.
 * Listening counts only while the session is open: app.mjs stops the
 * microphone otherwise, and the chip must not claim it in between. The words
 * for the session states are app.mjs's own (the journey waits on them). */
export function chipState(state, listening = false) {
  if (state === "active" && listening) return { key: "listening", ...CHIP.listening, timer: true, bars: true };
  const known = Object.hasOwn(CHIP, state) && state !== "listening" ? CHIP[state] : null;
  if (known) return { key: state, ...known, timer: false, bars: false };
  return { key: String(state ?? "offline"), word: state ? String(state) : "Offline", className: "chip-idle", timer: false, bars: false };
}

/** The full class list the chip element carries. */
export function chipClass(chip) {
  return `chip state-chip ${chip.className}`;
}

// ---------------------------------------------------------- the countdown

/** Milliseconds as M:SS, rounded up so the number never reads 0:00 while
 * time is left, and never below 0:00. */
export function formatCountdown(ms) {
  const total = Math.max(0, Math.ceil((Number.isFinite(ms) ? ms : 0) / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** What the keep-alive part says. remainingMs is null when unknown. */
export function keepAliveWords(remainingMs) {
  const tail = " unless a facilitator keeps it running.";
  if (remainingMs == null) return { before: "Capture pauses itself within 5 minutes" + tail, countdown: null, after: "", urgent: false };
  if (remainingMs <= 0) return { before: "Capture is due to pause now" + tail, countdown: null, after: "", urgent: true };
  return { before: "Capture pauses itself in ", countdown: formatCountdown(remainingMs), after: tail, urgent: remainingMs < URGENT_MS };
}

/** The lease as this screen can know it, from what it sees on each render:
 * the session state and `app.heartbeat`. See the module comment. */
export function createLease({ leaseMs = LEASE_MS, heartbeatMs = HEARTBEAT_MS } = {}) {
  let previous = null;   // the state at the last observation, null before the first
  let renewed = null;    // the latest renewal this screen knows of, ms
  let onSince = null;    // when the heartbeat was first seen on, ms
  return {
    observe({ now, state, heartbeat }) {
      if (state !== "active") {
        renewed = null; onSince = null; previous = state ?? null;
        return;
      }
      // An activation seen happening renews the lease. A session that was
      // already open at the first look has an unknown renewal.
      if (previous !== null && previous !== "active") renewed = Math.max(renewed ?? 0, now);
      if (heartbeat === true) {
        if (onSince === null) onSince = now;
        const beats = Math.floor((now - onSince) / heartbeatMs);
        if (beats >= 1) renewed = Math.max(renewed ?? 0, onSince + beats * heartbeatMs);
      } else {
        onSince = null;
      }
      previous = state;
    },
    /** Milliseconds left, at least 0, or null when unknown. */
    remaining(now) {
      return renewed === null ? null : Math.max(0, renewed + leaseMs - now);
    },
  };
}

// ------------------------------------------------------- the people line

/** People colours in join order (`members` is in join order): the five
 * accents, then their -deep steps. Initials are ink on an accent and paper
 * on a -deep step, the pairs tokens.css measures. */
export function personTone(index) {
  const n = (Math.max(0, index) % 10) + 1;
  return { fill: `var(--person-${n})`, text: n > 5 ? "var(--text-on-deep)" : "var(--text)" };
}

function initialOf(name) {
  const first = [...String(name ?? "").trim()][0];
  return first ? first.toLocaleUpperCase("en-GB") : "?";
}

/** The participant line: a circle per person, then who capture waits for. */
export function participantLine(s) {
  const members = s?.members ?? [];
  const waiting = s ? waitingFor(s) : [];
  const text = waiting.length ? `waiting for ${names(waiting)}` : "everyone agreed";
  const count = `${members.length} ${members.length === 1 ? "person" : "people"}`;
  return {
    people: members.map((m, i) => ({ id: m.id, name: m.name, initial: initialOf(m.name), agreed: agreed(s, m), ...personTone(i) })),
    text,
    // Said before the visible words, so the button's name holds them both.
    spoken: members.length ? `${count}: ${names(members)}. ` : `${count}. `,
  };
}

// ------------------------------------------------------ the commands

/** The eight command groups, in docs/COMMAND-PHRASES.md's words (three
 * examples each, copied verbatim so the sheet never teaches a phrase the
 * recogniser does not know; tests/header-unit.mjs checks them against the
 * file). `executed` is what voice_commands.py and the server carry out today:
 * the other four are recognised and nothing is made, and the menu and the
 * sheet say so. `start` is the phrase the menu sends, addressed exactly as a
 * person would say it. */
export const COMMAND_GROUPS = [
  { key: "voting", label: "Poll", executed: true, start: "create a poll",
    examples: ["create a poll", "let us vote", "start a poll"] },
  { key: "todo", label: "To-do list", executed: true, start: "make a to do list",
    examples: ["make a to do list", "create a task list", "give us an action list"] },
  { key: "requirements", label: "Requirements and wishes", executed: true, start: "make a requirements list",
    examples: ["make a requirements list", "prepare wishes", "show us a wish list"] },
  { key: "planning", label: "Calendar", executed: true, start: "create a calendar",
    examples: ["create a calendar", "make an agenda", "plan our next meeting"] },
  { key: "summary", label: "Summary", executed: true, start: "make a summary",
    examples: ["make a summary", "sum up this meeting", "give us the main points"] },
  { key: "visualisation", label: "Visualisation", executed: false,
    examples: ["create a diagram", "visualise this idea", "draw a picture"] },
  { key: "comparison", label: "Comparison", executed: false,
    examples: ["compare these ideas", "show us the differences", "list the similarities"] },
  { key: "suggestions", label: "Suggestions", executed: false,
    examples: ["make suggestions", "give us suggestions", "generate suggestions"] },
];

/** Said once on the sheet: how a list, the calendar and a poll are closed,
 * settled, reopened and dropped. Each phrase was checked against
 * voice_commands.py's recogniser; a poll has no reopen phrase. */
export const LIFECYCLE_WORDS = "Lists and the calendar collect from what is said until they are closed. " +
  "Say “Hey Jarvaids, close the to do list” to stop collecting, “accept the to do list” to settle it, " +
  "“reopen the to do list” to collect again, or “cancel the to do list” to drop it. " +
  "The same words work with “the requirements list” and “the calendar”. " +
  "For a poll: “close the poll”, “accept the results” or “cancel the poll”; a poll cannot be reopened.";

export const RECOGNISED_ONLY = "Recognised, not yet carried out";
export const RECOGNISED_ONLY_DETAIL = "Jarvaids hears this command and shows it in the transcript, but makes nothing from it yet.";

/** The words the menu sends for a group: the voice path's addressed form. */
export function commandText(key) {
  const group = COMMAND_GROUPS.find(g => g.key === key && g.executed);
  return group ? `Hey Jarvaids, ${group.start}.` : null;
}

/** Whether this member can start a command from the menu now, and if not,
 * why, in the words a disabled item carries. The menu sends a typed input
 * (source.text), which the server reads as a command only in the automatic
 * workspace and only from an editor while capture runs; a press that would
 * become a plain note instead is refused here. */
export function commandAvailability(s) {
  const state = s?.session?.state;
  const member = s?.members?.find(m => m.id === s.actor_id);
  if (!s?.session) return { enabled: false, reason: "Not connected to a session." };
  if (!["facilitator", "participant"].includes(member?.role)) return { enabled: false, reason: "Viewer access is read-only." };
  if (state === "closed") return { enabled: false, reason: "The session has ended." };
  if (state !== "active") return { enabled: false, reason: "Commands can be started while capture runs." };
  if (!s.session.automatic_workspace)
    return { enabled: false, reason: "In review mode, start a command by saying it. Typed commands run in the automatic workspace." };
  return { enabled: true, reason: "" };
}

/** What the attention line says after a command was sent. */
export function commandSentWords(key) {
  return {
    voting: "Asked for a poll. Its card on the canvas looks for the question and choices in the discussion.",
    todo: "Asked for a to-do list. Its card on the canvas collects tasks from what is said until someone closes it.",
    requirements: "Asked for a requirements list. Its card on the canvas collects requirements and wishes until someone closes it.",
    summary: "Asked for a summary. The Overview and canvas update when its queued batch is ready.",
    planning: "Asked for a calendar. Its card on the canvas collects dates and events until someone closes it.",
  }[key] ?? "Command sent.";
}

// --------------------------------------------------- the collecting chip

const COLLECTING_WORDS = { todo: "to-do", requirements: "requirements", calendar: "calendar" };

const byCreation = (a, b) => (a.data?.created_at ?? 0) - (b.data?.created_at ?? 0) || String(a.id).localeCompare(String(b.id));

/** The chip that says a command is gathering: a list or the calendar in
 * state "collecting", or a poll that is open. Only while capture runs,
 * because nothing is gathered while the session is paused or ended, and the
 * chip must not claim it. `targets` are the cards, newest first, that a
 * press shows in turn. Null when there is nothing to say. */
export function collectingPill(s) {
  if (s?.session?.state !== "active") return null;
  const records = s.records ?? [];
  const docs = records.filter(r => r.kind === "command_document" && r.data?.state === "collecting"
    && Object.hasOwn(COLLECTING_WORDS, r.data.document_type)).sort(byCreation);
  const polls = records.filter(r => r.kind === "poll" && r.data?.state === "open").sort(byCreation);
  if (!docs.length && !polls.length) return null;
  const types = [...new Set(docs.map(d => d.data.document_type))].map(t => COLLECTING_WORDS[t]);
  const words = [polls.length ? (polls.length === 1 ? "Poll open" : `${polls.length} polls open`) : "",
    types.length ? `Collecting: ${types.join(", ")}` : ""].filter(Boolean).join(" · ");
  const targets = [...docs, ...polls].sort(byCreation).reverse().map(r => r.id);
  const label = `${words}. Show ${targets.length > 1 ? "the next one" : "it"} on the canvas`;
  return { words, targets, label };
}

// ---------------------------------------------------------------- the tool

function createHeader() {
  let ctx = null;
  let last = null;           // the last snapshot rendered
  let announced = "";
  let ticker = 0;
  const lease = createLease();

  const el = id => ctx.$(id);
  const listening = () => Boolean(el("listen-status") && !el("listen-status").hidden);

  function paintChip(s) {
    const chip = chipState(s.session.state, listening());
    const box = el("session-status");
    box.className = chipClass(chip);
    box.dataset.state = chip.key;
    el("state-word").textContent = chip.word;
    el("state-bars").hidden = !chip.bars;
    if (announced !== chip.key) {
      announced = chip.key;
      el("state-announce").textContent = chip.word;
    }
  }

  function paintPeople(s) {
    const line = participantLine(s);
    const button = el("bar-members");
    const dots = document.createElement("span");
    dots.className = "people-dots";
    dots.setAttribute("aria-hidden", "true");
    for (const p of line.people) {
      const dot = document.createElement("span");
      dot.className = "person-dot";
      dot.title = p.name;
      dot.textContent = p.initial;
      dot.style.setProperty("--person", p.fill);
      dot.style.setProperty("--person-text", p.text);
      dots.append(dot);
    }
    const spoken = document.createElement("span");
    spoken.className = "visually-hidden";
    spoken.textContent = line.spoken;
    const words = document.createElement("span");
    words.className = "people-words";
    words.textContent = line.text;
    button.replaceChildren(dots, spoken, words);
  }

  function paintKeepAlive() {
    const words = keepAliveWords(lease.remaining(Date.now()));
    const text = el("keepalive-text");
    if (words.countdown) {
      const count = document.createElement("span");
      count.className = "t-mono capture-countdown";
      count.id = "keepalive-countdown";
      count.textContent = words.countdown;
      text.replaceChildren(words.before, count, words.after);
    } else {
      text.replaceChildren(words.before);
    }
    return words.urgent;
  }

  function paintBanner() {
    const banner = el("capture-banner");
    const parts = { paused: el("paused-banner"), keepalive: el("keepalive-banner"), ended: el("ended-banner") };
    const shown = Object.keys(parts).find(k => !parts[k].hidden) ?? "";
    // The agreement screen explains a pause in its own words; everywhere
    // else the banner says what capture is doing.
    const onGate = ctx.app.screen === "setup" || !el("screen-setup")?.hidden;
    const urgent = shown === "keepalive" ? paintKeepAlive() : false;
    banner.dataset.state = shown;
    banner.classList.toggle("is-urgent", urgent);
    banner.hidden = !shown || onGate;
  }

  // ---- the Jarvaids menu, the sheet and the collecting chip

  let sending = false;       // one command at a time, as the composer adds one note at a time
  let pillTargets = [];      // the cards the collecting chip shows, newest first
  let pillKey = "";
  let pillTurn = 0;

  const menuItems = () => [...el("command-menu").querySelectorAll('[role="menuitem"]')];
  const menuOpen = () => !el("command-menu").hidden;

  /** Opens or closes the menu. Opening moves focus to the first or last
   * item, as a menu button does; closing from inside gives it back. */
  function setMenu(open, focus = null) {
    el("command-menu").hidden = !open;
    el("command-menu-button").setAttribute("aria-expanded", String(open));
    if (open && focus) (focus === "last" ? menuItems().at(-1) : menuItems()[0])?.focus();
    if (!open && focus === "button") el("command-menu-button").focus();
  }

  function moveInMenu(key) {
    const items = menuItems();
    const at = items.indexOf(document.activeElement);
    const next = key === "Home" ? 0 : key === "End" ? items.length - 1
      : (at + (key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
    items[next]?.focus();
  }

  /** An unavailable item stays reachable by the arrow keys (aria-disabled,
   * not disabled), so its reason can be read; it does nothing when chosen. */
  function paintMenu(s) {
    const can = commandAvailability(s);
    const reason = sending ? "Sending the previous command." : can.reason;
    for (const item of el("command-menu").querySelectorAll("[data-command]")) {
      const off = sending || !can.enabled || (item.dataset.command === "summary" && !s?.session?.summary_ai?.available);
      if (off) {
        item.setAttribute("aria-disabled", "true");
        const why = item.dataset.command === "summary" && !s?.session?.summary_ai?.available ? "Summaries are not enabled on this server." : reason;
        item.title = why;
        item.setAttribute("aria-description", why);
      } else {
        for (const name of ["aria-disabled", "title", "aria-description"]) item.removeAttribute(name);
      }
    }
  }

  /** Sends the addressed words through the same typed route as the
   * composer (source.text), so the record says this person asked for it
   * and the transcript shows the words, as if they had said them. */
  async function startCommand(key) {
    const text = commandText(key);
    if (!text || sending || !commandAvailability(ctx.app.snapshot).enabled) return;
    sending = true;
    paintMenu(ctx.app.snapshot);
    try {
      await ctx.send("source.text", { text });
      ctx.attention(commandSentWords(key), "note");
    } catch {
      // send() has already said why in the attention banner.
    } finally {
      sending = false;
      if (ctx.app.snapshot) paintMenu(ctx.app.snapshot);
    }
  }

  function fillSheet() {
    const make = (tag, className, text) => {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = text;
      return node;
    };
    const section = (title, groups, note) => {
      const box = make("section", "commands-section");
      box.append(make("h3", "t-body commands-section-title", title));
      if (note) box.append(make("p", "t-body commands-note", note));
      const grid = make("div", "commands-grid");
      for (const g of groups) {
        const group = make("div", "commands-group");
        group.dataset.group = g.key;
        group.append(make("h4", "t-body commands-group-title", g.label));
        const list = make("ul", "commands-phrases");
        for (const phrase of g.examples) list.append(make("li", "t-body", phrase));
        group.append(list);
        grid.append(group);
      }
      box.append(grid);
      return box;
    };
    el("commands-body").replaceChildren(
      section("Carried out on the canvas", COMMAND_GROUPS.filter(g => g.executed)),
      section(RECOGNISED_ONLY, COMMAND_GROUPS.filter(g => !g.executed), RECOGNISED_ONLY_DETAIL),
      make("p", "t-body commands-lifecycle", LIFECYCLE_WORDS));
  }

  const sheetOpen = () => !el("commands-sheet").hidden;
  function openSheet() {
    el("commands-sheet").hidden = false;
    el("close-commands").focus();
  }
  function closeSheet() {
    if (!sheetOpen()) return;
    el("commands-sheet").hidden = true;
    el("command-menu-button").focus();
  }

  function paintPill(s) {
    const pill = el("collecting-pill");
    const info = collectingPill(s);
    pill.hidden = !info;
    pillTargets = info?.targets ?? [];
    if (!info) return;
    const key = info.targets.join();
    if (key !== pillKey) { pillKey = key; pillTurn = 0; }
    el("collecting-words").textContent = info.words;
    pill.setAttribute("aria-label", info.label);
    pill.title = info.label;
  }

  /** Shows the next collecting card. On the canvas, board.mjs pans to a
   * command card it has not shown yet (its seenPolls set), the move it
   * makes when one is created; forgetting this card asks for that move
   * again and changes nothing else. In List view, the card scrolls in. */
  function showCollecting() {
    if (!pillTargets.length) return;
    const id = pillTargets[pillTurn % pillTargets.length];
    pillTurn += 1;
    if (ctx.app.screen !== "workspace") ctx.screen("workspace");
    if (ctx.app.view === "canvas" && ctx.board?.seenPolls) {
      ctx.board.seenPolls.delete(id);
      ctx.render();
      // Below the breakpoint the rail comes first, so the board itself may be
      // below the fold: bring it into the window too.
      el("board")?.scrollIntoView({ block: "nearest" });
    } else {
      document.querySelector(`#list-view [data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "nearest" });
    }
  }

  function wireCommands() {
    const button = el("command-menu-button"), menu = el("command-menu");
    if (!button || !menu || button.dataset.wired) return;
    button.dataset.wired = "true";
    button.addEventListener("click", () => setMenu(!menuOpen(), "first"));
    button.addEventListener("keydown", event => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      event.preventDefault();
      setMenu(true, event.key === "ArrowUp" ? "last" : "first");
    });
    menu.addEventListener("keydown", event => {
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) { event.preventDefault(); moveInMenu(event.key); }
      else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setMenu(false, "button"); }
      else if (event.key === "Tab") setMenu(false);
    });
    menu.addEventListener("click", event => {
      const item = event.target.closest('[role="menuitem"]');
      if (!item || item.getAttribute("aria-disabled") === "true") return;
      setMenu(false, "button");
      if (item.dataset.command) startCommand(item.dataset.command);
      else if (item.id === "open-commands") openSheet();
    });
    for (const item of menu.querySelectorAll("[data-recognised]")) {
      item.title = RECOGNISED_ONLY;
      item.setAttribute("aria-description", `${RECOGNISED_ONLY}. ${RECOGNISED_ONLY_DETAIL}`);
    }
    document.addEventListener("click", event => {
      if (menuOpen() && !event.target.closest("#command-menu-wrap")) setMenu(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      if (menuOpen()) setMenu(false, "button");
      else if (sheetOpen()) closeSheet();
    });
    fillSheet();
    el("close-commands").addEventListener("click", () => closeSheet());
    el("commands-sheet").addEventListener("click", event => { if (event.target === el("commands-sheet")) closeSheet(); });
    el("collecting-pill").addEventListener("click", () => showCollecting());
  }

  function sync() {
    if (!ctx || !last?.session) return;
    paintChip(last);
    paintBanner();
  }

  return {
    mount(context) {
      ctx = context;
      wireCommands();
      const watch = new MutationObserver(() => sync());
      for (const id of ["listen-status", "screen-setup", "paused-banner", "keepalive-banner", "ended-banner"]) {
        const target = el(id);
        if (target) watch.observe(target, { attributes: true, attributeFilter: ["hidden"] });
      }
      // Only the countdown needs the clock; the listening timer is app.mjs's.
      clearInterval(ticker);
      ticker = setInterval(() => {
        if (last?.session && !el("keepalive-banner").hidden && !el("capture-banner").hidden) paintBanner();
      }, 1000);
    },
    render(context, s) {
      ctx = context;
      last = s;
      lease.observe({ now: Date.now(), state: s.session.state, heartbeat: ctx.app.heartbeat });
      paintChip(s);
      paintPeople(s);
      paintBanner();
      paintPill(s);
      paintMenu(s);
    },
  };
}

export function register(registerTool) {
  registerTool("header", createHeader());
}

export { createHeader };
