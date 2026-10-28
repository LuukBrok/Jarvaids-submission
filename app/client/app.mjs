/**
 * Jarvaids client.
 *
 * Built around the meeting's flow (docs/ux-flows-2026-10-18.md): join or
 * start, agree, then one workspace where the room captures, reviews and
 * arranges. The session bar carries the session's honest state, this
 * device's recording, the people and their agreement, the two inputs
 * (photograph, listen), Undo and Pause. Beside the canvas, one non-modal
 * panel holds Review, Transcript and People.
 *
 * Deliberately thin: `client.mjs` owns the transport, `session-sync.mjs` the
 * state (deltas, resync, board order, the control lane and the heartbeat),
 * `capture-audio.mjs` the microphone, `board.mjs` the canvas, and
 * `review.mjs`, `people.mjs` and `photo.mjs` their panels. This file is
 * wiring and the screens around them.
 *
 * Three product rules are enforced on screen rather than assumed:
 *
 *   Automatic inputs retain model/source labels and never claim human
 *   acceptance. Legacy review mode still distinguishes proposed work.
 *
 *   The screen never says something is recorded when it is not: "Session
 *   open" is not "Recording"; Recording, with a timer, means this device's
 *   microphone is on.
 *
 *   A success message is only shown after the server said yes.
 *
 * No build step. Loaded as an ES module straight from disk.
 */
import { GenAIClient, newId, newToken, ApiError, RequestError } from "../server/client.mjs";
import { SessionConnection, ConnectionError } from "../server/session-sync.mjs";
import { startCapture } from "../server/capture-audio.mjs";
import { renderTranscript } from "./transcript.mjs";
import { renderOverview } from "./overview.mjs";
import { WakeConfirmation } from "./wake-confirmation.mjs";
import { recordVoiceSample } from "./speakers.mjs";
import { WakewordController, WakewordChime } from "../server/wakeword.mjs";
import { Board, boardModel, machineMade, memberName, noteMeta, objectMeta } from "./board.mjs";
import { pollElement } from "./polls.mjs";
import { documentElement } from "./documents.mjs";
import { objectLabel } from "./canvas-objects.mjs";
import { addAndAccept, addAndAcceptMessage } from "./composer.mjs";
import { createReview, mayReadCrop } from "./review.mjs";
import { createPeople, waitingFor, names, agreed } from "./people.mjs";
import { createPhoto } from "./photo.mjs";
// Phase 3's tools. Each module exports register(registerTool) and touches
// nothing else here, so parallel work never edits this file (DESIGN.md 2).
import * as headerTool from "./header.mjs";
import * as dockTool from "./tools/dock.mjs";
import * as drawTool from "./tools/draw.mjs";
import * as connectTool from "./tools/connect.mjs";
import * as stripTool from "./tools/strip.mjs";
import * as quoteTool from "./tools/quote.mjs";
import * as parkedTool from "./tools/parked.mjs";
import { parkedNotes, parkedSections } from "./tools/parked.mjs";
import * as threadsTool from "./tools/threads.mjs";
// The Calendar view, the third view beside Canvas and List.
import * as calendarViewTool from "./calendar-view.mjs";

let enrolmentAbort, wakeController;
const wakeChime = new WakewordChime();
const wakeConfirmation = new WakeConfirmation(() => { $("wakeword-status").textContent = "Hey Jarvaids confirmed in speech"; wakeChime.play(); });
const $ = id => document.getElementById(id);
const show = (el, on) => { if (el) el.hidden = !on; };
const coarse = window.matchMedia?.("(pointer: coarse)").matches ?? false;

const app = {
  client: null,
  connection: null,
  snapshot: null,
  screen: "setup",
  rail: "review",
  // On a phone the list is the default view: the board is read only there.
  view: coarse ? "list" : "canvas",
  photo: null,        // {file, dataUrl, regions:[{id, box}]}
  photoJob: null,     // the job the photo flow is following
  controlSequence: 1,
  drafts: new Map(),  // proposal id -> {revision, text}: a correction in progress survives a refresh
  crops: new Map(),   // proposal id:revision -> blob URL, null while loading, false if refused
  dismissedJobs: new Set(),
  undoStack: [],      // items this person accepted, newest last
  lastAccepted: null,
  batching: false,    // two commands behind one press: no read between them
  focusProposal: null,
  mic: null,
  listenStarted: 0,
  board: null,
};

// ---------------------------------------------------------------- attention

/** One banner that stays until it is dismissed or replaced. Never the kind
    that appears and disappears on a timer: a message about a meeting's record
    must not be missable. */
function attention(message, kind = "problem", { choices = false } = {}) {
  const el = $("attention");
  $("attention-text").textContent = message;
  el.dataset.kind = kind;
  $("attention-glyph").className = "glyph " + (kind === "problem" ? "glyph-failed st-failed" : "glyph-accepted st-accepted");
  // While the banner offers Try again and Discard, those are the way out:
  // Dismiss would hide a command that still blocks every other control.
  const offering = Boolean(message) && choices;
  show($("attention-actions"), offering);
  show($("attention-dismiss"), !offering);
  show(el, Boolean(message));
}

/** What each control command is called in the uncertain banner. */
const CONTROL_NAMES = {
  "session.pause": "the pause", "session.close": "ending the session", "session.heartbeat": "keeping capture running",
  "participant.remove": "the removal", "consent.withdraw": "withdrawing agreement", "invitation.revoke": "revoking the invitation",
};

/** A control command whose outcome is unknown is kept by the sync library,
 * which refuses every later control until a person chooses (DESIGN.md 1.4).
 * Before phase 4 the client offered no choice, so Pause, End and Remove
 * stayed blocked until a reload. Returns whether one is pending. */
function uncertainBanner(reason = "") {
  const pending = app.connection?.pendingControl;
  if (!pending) return false;
  const what = CONTROL_NAMES[pending.operation] ?? "that";
  attention(`${reason ? reason + " " : ""}The server may or may not have applied ${what}. Nothing was retried automatically: ` +
    "Try again sends the same command, which the server applies at most once; Discard drops it, so check the screen before doing it again.",
    "problem", { choices: true });
  return true;
}

async function retryControl() {
  try {
    await app.connection.retryPendingControl();
    attention("");
    await refresh();
  } catch (error) {
    if (!uncertainBanner(error?.outcome === "unknown" ? "" : describe(error))) attention(describe(error));
  }
}

function discardControl() {
  const pending = app.connection?.pendingControl;
  try {
    app.connection.discardPendingControl();
    attention(`Dropped ${CONTROL_NAMES[pending?.operation] ?? "that command"}. It may or may not have happened: the screen refreshes from the server, so check it before doing it again.`, "note");
    render();
  } catch (error) { attention(describe(error)); }
}

const ERROR_WORDS = {
  invalid_join_code: "That invitation is not complete. Check that the whole code was copied.",
  invitation_expired: "This invitation has expired. Ask the facilitator for a new one.",
  invitation_consumed: "This invitation was already used. Ask the facilitator for a new one.",
  invalid_invitation: "That invitation does not match this session. Ask the facilitator for a new one.",
  policy_changed: "The session's agreement changed since this invitation was made. Ask the facilitator for a new one.",
  session_closed: "This session has ended and is not accepting people.",
  agreement_incomplete: "Not everyone has agreed yet, so capture cannot start.",
  unreadable_content: "Type what the note says before accepting it.",
};

function describe(error) {
  // The control lane wraps the server's answer; a refusal is not a lost connection.
  if (error instanceof ConnectionError && error.cause instanceof ApiError) return describe(error.cause);
  if (ERROR_WORDS[error?.code]) return ERROR_WORDS[error.code];
  if (error instanceof ApiError) {
    // The outcome matters more than the code: an uncertain write must never be
    // reported as a failure, or people retry things that already happened.
    const uncertain = error.outcome === "unknown";
    return (uncertain ? "Uncertain, so nothing was retried automatically: " : "") + (error.message || error.code);
  }
  if (error instanceof RequestError || error instanceof ConnectionError) {
    return error.outcome === "unknown"
      ? "The server may or may not have applied that. Nothing was retried automatically."
      : "Could not reach the server. Check the server address and the connection.";
  }
  return String(error?.message ?? error);
}

// ------------------------------------------------------------------ commands

const CONTROL = new Set(["session.pause", "session.close", "session.heartbeat",
                         "participant.remove", "consent.withdraw", "invitation.revoke"]);

/** Every command goes through here, so control sequencing is in one place. */
async function send(operation, payload = {}, options = {}) {
  const control = CONTROL.has(operation);
  try {
    let result;
    if (control && app.connection) {
      // One control lane, shared with the heartbeat (CLIENT-PLUMBING.md): the
      // server numbers control commands per person, so a second counter here
      // would collide with a heartbeat sent in the same second.
      result = (await controlLane(operation, payload)).result;
    } else {
      const intent = app.client.intent(operation, payload,
        control ? { controlSequence: app.controlSequence } : {});
      result = await app.client.submit(intent, options);
      if (control) app.controlSequence += 1;
      // The reply is not merged into the snapshot; ask for the next read now
      // rather than at the interval, so what this person did shows at once.
      // Not in the middle of a pair of commands behind one press: the read
      // would show the first half (a note proposed) for a moment before the
      // second (accepted), and the room would see it flicker.
      if (!app.batching) app.connection?.pollSoon?.();
    }
    attention("");
    app.lastAccepted = operation === "proposal.review" ? app.lastAccepted : null;
    if (operation === "canvas.remove") rememberRemoval(payload, result.result);
    await refresh();
    return result.result;
  } catch (error) {
    if (!(control && uncertainBanner())) attention(describe(error));
    throw error;
  }
}

/** A heartbeat in flight holds the lane for a moment; wait for it rather than
 * fail a person's Pause. Nothing else is retried. */
async function controlLane(operation, payload) {
  for (let attempt = 0; ; attempt++) {
    try { return await app.connection.submitControl(operation, payload); }
    catch (error) {
      if (error?.code !== "control_busy" || attempt >= 20) throw error;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
}

/** Capture's lease runs out five minutes after the last heartbeat, so an
 * active facilitator's open screen renews it. Enabled by starting or resuming
 * capture, or by pressing "Keep capture running" after this screen was hidden
 * or offline; never re-enabled behind anyone's back. */
function keepCaptureRunning() {
  try { app.connection?.enableHeartbeat(); app.heartbeat = true; }
  catch { app.heartbeat = false; }
  render();
}

async function refresh() {
  if (!app.connection) return;
  app.snapshot = app.connection.snapshot;
  if (app.snapshot?.next_control_sequence) app.controlSequence = app.snapshot.next_control_sequence;
  render();
}

function button(label, variant, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `btn ${variant}`;
  b.textContent = label;
  b.addEventListener("click", () => onClick().catch(() => {}));
  return b;
}

function clock(seconds) {
  return new Date(seconds * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function dateTime(seconds) {
  return new Date(seconds * 1000).toLocaleString("en-GB", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", hour12: false });
}

/** The one modal: a confirmation for what cannot be undone. Cancel is focused,
 * because the safe answer must be the easy one. */
function confirm({ title, text, detail = "", action, danger = true }) {
  const dialog = $("confirm-dialog");
  $("confirm-title").textContent = title;
  $("confirm-text").textContent = text;
  $("confirm-detail").textContent = detail;
  const ok = $("confirm-ok");
  ok.textContent = action;
  ok.className = "btn " + (danger ? "btn-danger-fill" : "btn-primary");
  return new Promise(resolve => {
    const finish = value => { dialog.close(); ok.onclick = null; $("confirm-cancel").onclick = null; resolve(value); };
    ok.onclick = () => finish(true);
    $("confirm-cancel").onclick = () => finish(false);
    dialog.oncancel = event => { event.preventDefault(); finish(false); };
    dialog.showModal();
    $("confirm-cancel").focus();
  });
}

// ------------------------------------------------------------------ modules

const ctx = { app, $, show, send, attention, describe, render, button, confirm, clock,
  screen, rail, undo, stopListening, settle, machineMade, boardModel, memberName, view: setView };
// The board is made in wire(), after this object, so it is read through.
Object.defineProperty(ctx, "board", { get: () => app.board, enumerable: true });
const review = createReview(ctx);
const people = createPeople(ctx);
ctx.review = review;
const photo = createPhoto(ctx);

// -------------------------------------------------------------------- tools

/** The tool registry. A tool is a name and up to four hooks, all optional:
 *   mount(ctx)             once, from wire(), after the board exists
 *   render(ctx, snapshot)  at the end of every render() that has a snapshot
 *   onSelection(ids)       when the board's selection changes (array of ids)
 *   onZoom(z)              when the board's zoom changes (1 is 100%)
 * Tools run in registration order. A hook that throws is reported on the
 * console and does not stop the others or the render, so one broken tool
 * cannot take the workspace with it; the browser tests fail on any console
 * error, so it is still caught. */
const tools = new Map();

function registerTool(name, hooks = {}) {
  if (typeof name !== "string" || !name) throw new TypeError("registerTool needs a name");
  if (tools.has(name)) throw new Error(`A tool called "${name}" is already registered`);
  tools.set(name, hooks);
}

function callTools(hook, ...args) {
  for (const [name, hooks] of tools) {
    if (typeof hooks[hook] !== "function") continue;
    try { hooks[hook](...args); }
    catch (error) { console.error(`Tool "${name}" failed in ${hook}:`, error); }
  }
}

for (const tool of [headerTool, dockTool, drawTool, connectTool, stripTool, quoteTool, parkedTool, threadsTool, calendarViewTool]) {
  tool.register(registerTool);
}

/** Adds a motion class (note-landing, note-accepting, note-rejecting) and
 * resolves when its animation ends. With reduced motion there is no
 * animation, so it resolves at once; a safety timeout covers an animation
 * that never starts. The class is removed afterwards unless keep is true. */
function settle(el, className, { keep = false, timeoutMs = 1000 } = {}) {
  return new Promise(resolve => {
    if (!el) { resolve(); return; }
    let timer = 0;
    const done = event => {
      // A child's own animation (a chip's bars) bubbles here too; only this
      // element's counts.
      if (event && event.target !== el) return;
      clearTimeout(timer);
      el.removeEventListener("animationend", done);
      el.removeEventListener("animationcancel", done);
      if (!keep) el.classList.remove(className);
      resolve();
    };
    el.classList.add(className);
    const names = getComputedStyle(el).animationName;
    if (!names || names === "none") { done(); return; }
    el.addEventListener("animationend", done);
    el.addEventListener("animationcancel", done);
    timer = setTimeout(() => done(), timeoutMs);
  });
}

// -------------------------------------------------------------------- render

/** The session's state in words. header.mjs draws the chip around them
 * (its look, the bars, the timer); the journey waits on these words. */
const SESSION_WORDS = { active: "Session open", paused: "Paused", draft: "Not started", closed: "Ended" };

function me(s) { return s.members.find(m => m.id === s.actor_id); }

function render() {
  const s = app.snapshot;
  show($("bar"), Boolean(s) && s.session?.state !== "deleted");
  if (!s || !s.session) return;
  const mine = me(s);
  const facilitator = mine?.role === "facilitator";
  const state = s.session.state;
  const active = state === "active";

  // The session's state, and separately this device's recording.
  $("state-word").textContent = SESSION_WORDS[state] ?? state;
  $("bar-title").textContent = s.session.title ?? "";
  const waiting = waitingFor(s);
  $("bar-members").textContent = `${s.members.length} ${s.members.length === 1 ? "person" : "people"} · ` +
    (waiting.length ? `${s.members.length - waiting.length} agreed` : "everyone agreed");
  $("listen").disabled = !active && !app.mic;
  $("open-photo").disabled = !active;
  show($("stop-capture"), active);
  $("stop-capture").disabled = !active;
  if (!active && app.mic) stopListening();
  show($("undo"), facilitator && app.undoStack.length > 0 && state !== "closed");
  show($("end-session"), facilitator && state !== "closed");
  show($("delete-session"), facilitator);
  show($("open-export"), facilitator);

  const needed = !mine || !agreed(s, mine);
  renderGate(s, needed, facilitator);
  // The workspace opens once this person has agreed and capture has started
  // at least once. Withdrawing brings the agreement back to the front.
  const started = ["active", "paused", "closed"].includes(state);
  if (needed && state !== "closed" && app.screen !== "setup") screen("setup");
  else if (app.screen === "setup" && !needed && started) screen("workspace");

  // On the agreement screen the workspace's actions are not offered yet, and
  // the product's own heading gives way to the session's.
  show($("bar-actions"), app.screen !== "setup");
  show($("page-head"), false);

  show($("paused-banner"), state === "paused");
  const withdrew = s.members.filter(m => !agreed(s, m) && m.withdrawn_at);
  $("paused-reason").textContent = withdrew.length
    ? `Paused because ${names(withdrew)} withdrew agreement. Capture can resume once everyone has agreed again.`
    : "Nothing new is being recorded. The canvas and review still work.";
  $("resume").hidden = !facilitator;
  $("resume").disabled = waiting.length > 0;
  show($("ended-banner"), state === "closed");
  if (state === "closed") $("ended-text").textContent =
    `This session has ended. The canvas can still be read and exported until ${dateTime(s.session.expires)}.`;

  // A command still uncertain comes back to the banner whenever the banner
  // is free, because until someone chooses, every control stays refused.
  if (app.connection?.pendingControl && $("attention").hidden) uncertainBanner();

  const facilitating = facilitator && active;
  if (!facilitating) app.heartbeat = false;
  if (facilitating && app.wantHeartbeat && !app.heartbeat) { app.wantHeartbeat = false; keepCaptureRunning(); return; }
  show($("keepalive-banner"), facilitating && !app.heartbeat);

  const proposals = s.records.filter(r => r.kind === "proposal" && ["needs_review", "stale"].includes(r.data.status));
  $("queue-count").textContent = String(proposals.length);
  review.renderQueue(s, proposals);
  if (s.session.automatic_workspace) {
    if (!app.automaticOpened) { app.automaticOpened = true; rail("transcript"); }
    $("queue-empty").textContent = "Everything is added automatically. Edit notes on the canvas whenever needed.";
  }
  renderTranscript(s);
  wakeConfirmation.update(s, Boolean(app.mic));
  renderOverview(s, send);
  people.renderPeople(s);
  $("speaker-enrol").disabled = !active || Boolean(enrolmentAbort);
  if (!active) enrolmentAbort?.abort();

  for (const id of ["add-note", "add-accept", "note-text"]) $(id).disabled = !active;
  // Accepting is a facilitator's, so only a facilitator is offered both at once.
  show($("add-accept"), facilitator && !s.session.automatic_workspace);
  $("note-text").placeholder = active ? "Type what someone said or wrote" : "Notes can be added while capture runs";

  if (app.screen === "workspace") {
    const drawn = boardModel(s);
    const empty = drawn.notes.length === 0 && drawn.objects.length === 0 && drawn.polls.length === 0 && drawn.documents.length === 0;
    show($("board-empty"), empty && app.view === "canvas");
    // The empty card's promise follows the server's mode: automatic
    // workspace applies notes at once and keeps them editable; review mode
    // holds them as proposals until someone accepts them.
    $("board-empty-copy").textContent = s.session.automatic_workspace
      ? "Photograph the sticky notes or type one in: each lands here, labelled, and stays editable."
      : "Photograph the sticky notes or type one in: each lands here as a proposal until someone accepts it.";
    app.board.render(s);
    const topics = app.board.isTopicLayout(s);
    show($("topic-layout"), app.view === "canvas" && s.records.some(r => r.kind === "summary_topic"));
    $("topic-layout").textContent = topics ? "By topic" : "Free layout";
    $("topic-layout").setAttribute("aria-pressed", String(topics));
    show($("topic-layout-hint"), topics && app.view === "canvas");
    if (app.view === "list") renderList(s);
    show($("arrange"), !s.session.automatic_workspace && app.view === "canvas" && unplaced(s).length > 0 && state !== "closed");
  }
  photo.renderReading(s);
  if (app.screen === "export") renderExport(s);
  callTools("render", ctx, s);
}

function renderGate(s, needed, facilitator) {
  show($("start-join"), false);
  show($("consent"), true);
  $("consent-session").textContent = s.session.title ?? "";
  $("consent-text").textContent =
    `This session records what is said, typed and photographed here. The session record is stored on the server you ` +
    `connected to, and everything in it is deleted on ${dateTime(s.session.expires)}. ` +
    (s.session.poll_ai?.cloud_text
      ? "While setting up or running a poll, relevant transcript text is sent to Anthropic for AI interpretation. Voice choices keep their source information. "
      : "Cloud poll interpretation is unavailable or disabled. ") +
    (s.session.command_ai?.whole_meeting_text
      ? "When you request a to-do list, requirements and wishes, or a calendar, the original transcript from this whole meeting so far and its list entries are sent to Anthropic, followed by new discussion while collecting. Model suggestions are labelled. "
      : "Cloud document interpretation is unavailable or disabled; manual controls remain available. ") +
    (s.session.automatic_workspace ? "Notes and command results are added automatically and stay editable. When the real photo reader is enabled, the whole sanitised photograph is sent to Anthropic to find and read the notes. " : "When the real photo reader is enabled, marked photograph regions are sent to Anthropic for handwriting reading. ") +
    (s.session.summary_ai?.available
      ? (s.session.summary_ai.local ? "Rolling topic summaries run locally. " : "Rolling topic summaries send transcript text and the existing topic overview to Anthropic. ")
      : "") + "Audio and voice profiles stay on this server.";
  show($("agree-line"), needed);
  show($("acknowledge"), needed);
  $("acknowledge").disabled = !needed || !$("agree-check").checked;
  const mine = me(s);
  show($("agreed-note"), !needed);
  if (!needed) $("agreed-note").textContent = mine?.agreed_at ? `You agreed at ${clock(mine.agreed_at)}.` : "You agreed.";
  people.renderRows(s, $("consent-rows"), { manage: false });

  const waiting = waitingFor(s);
  show($("activate"), facilitator);
  $("activate").textContent = s.session.state === "paused" ? "Resume capture" : "Start capture";
  $("activate").disabled = waiting.length > 0 || s.session.state === "active";
  $("activate-reason").textContent = s.session.state === "active" ? "Capture is running."
    : waiting.length ? `Waiting for ${names(waiting)} to agree.`
    : facilitator ? "Everyone has agreed." : "The facilitator starts capture once everyone has agreed.";
}

// ------------------------------------------------------------------ the list

const STATUS_MARKUP = {
  accepted: ["status st-accepted", '<i class="glyph glyph-accepted" aria-hidden="true"></i><span class="word">Accepted</span>'],
  automatic: ["status st-provisional", '<i class="glyph glyph-provisional" aria-hidden="true"></i><span class="word">Automatic</span>'],
  proposed: ["status st-provisional", '<i class="glyph glyph-provisional" aria-hidden="true"></i><span class="word">Proposed</span>'],
  pending: ["status st-off", '<span class="word">Not yet reviewed</span>'],
};

/** One row of the list: status, what it is, who made or accepted it. */
function listRow(state, words, metaText, reviewId) {
  const row = document.createElement("div");
  row.className = "list-row";
  const status = document.createElement("span");
  [status.className, status.innerHTML] = STATUS_MARKUP[state];
  const text = document.createElement("span");
  text.className = "t-body";
  text.textContent = words;
  const meta = document.createElement("span");
  meta.className = "t-meta";
  meta.textContent = metaText;
  row.append(status, text, meta);
  if (reviewId) row.append(button("Review", "btn-quiet btn-sm", async () => reviewFromBoard(reviewId)));
  return row;
}

/** The canvas's parallel list: everything the canvas draws, in words. */
export function renderList(s) {
  const model = boardModel(s);
  const box = $("list-view");
  const active = document.activeElement;
  const focus = box.contains(active) ? active.dataset.focusKey : null;
  const caret = typeof active?.selectionStart === "number" ? [active.selectionStart, active.selectionEnd] : null;
  box.textContent = "";
  for (const poll of model.polls) box.append(pollElement(s, poll, { send, attention }, app.board.pollDrafts));
  for (const doc of model.documents) box.append(documentElement(s, doc, { send, attention }, app.board.documentDrafts, { fullCalendar: true }));
  const section = (title, rows) => {
    if (!rows.length) return;
    const wrap = document.createElement("section");
    const h = document.createElement("h2");
    h.className = "t-title";
    h.textContent = title;
    const list = document.createElement("div");
    list.append(...rows);
    wrap.append(h, list);
    box.append(wrap);
  };
  const noteRows = notes => notes.map(n => listRow(
    n.data.automatic ? "automatic" : n.kind === "item" ? "accepted" : machineMade(n) ? "proposed" : "pending",
    n.data.text, noteMeta(s, n), n.kind === "proposal" ? n.id : null));
  // The parked margin's notes are on the shelf, not on the board, and the
  // shelf's own section record is the shelf, not a section a person drew;
  // the list says so in the canvas's words instead of "Section · Parked".
  const parked = parkedNotes(s);
  const shelves = new Set(parkedSections(s).map(r => r.id));
  const onBoard = model.notes.filter(n => !parked.has(n.id));
  for (const c of model.clusters) section(`Group · ${c.data.text}`, noteRows(onBoard.filter(n => model.groupOf.get(n.id)?.id === c.id)));
  for (const c of model.proposedClusters) {
    section(`Proposed group · ${c.data.text}`, noteRows(c.data.refs.map(ref => onBoard.find(n => n.id === ref.id)).filter(Boolean)));
  }
  section("Not in a group", noteRows(onBoard.filter(n => !model.groupOf.has(n.id))));
  section("Parked shelf", noteRows(model.notes.filter(n => parked.has(n.id))));
  // A canvas proposal is a model's, so it is always drawn proposed.
  section("Shapes, sections and drawings", model.objects.filter(o => !shelves.has(o.id)).map(o => listRow(o.proposed ? "proposed" : "accepted",
    objectLabel(o, model.nameOf), objectMeta(s, o), o.proposed ? o.id : null)));
  if (!model.notes.length && !model.objects.length && !model.polls.length && !model.documents.length) {
    const p = document.createElement("p");
    p.className = "t-body empty";
    p.textContent = "Nothing on the canvas yet. Photograph the wall or add a note.";
    box.append(p);
  }
  if (focus) {
    const target = box.querySelector(`[data-focus-key="${focus}"]`);
    target?.focus();
    if (caret && target?.setSelectionRange) target.setSelectionRange(...caret);
  }
}

function reviewFromBoard(id) {
  app.focusProposal = id;
  $("summary-flush").addEventListener("click", () => send("summary.flush").catch(() => {}));
  $("summary-save").addEventListener("click", () => send("summary.configure", {
    agenda: $("summary-agenda").value.split("\n").map(v => v.trim()).filter(Boolean), enabled: $("summary-enabled").checked,
  }).catch(() => {}));
  rail("review");
  render();
  const row = document.querySelector(`.proposal[data-id="${id}"]`);
  row?.scrollIntoView({ block: "nearest" });
  row?.querySelector("textarea")?.focus();
}

// ------------------------------------------------------------ arrange notes

/** Accepted notes nobody has placed yet. */
function unplaced(s) {
  return boardModel(s).notes.filter(n => n.kind === "item" && !n.position);
}

/** "Place new notes": lays out accepted, unplaced notes by group, then by the
 * photograph they came from, to the right of what is already placed, or in a
 * band under it once the wall is as wide as the board at 100%. It is a
 * machine placement, so the server refuses it onto anything a person placed
 * by hand; and it moves nothing that already has a place. */
async function arrange() {
  const s = app.snapshot;
  const model = boardModel(s);
  const todo = unplaced(s);
  if (!todo.length) return;
  const placed = model.notes.filter(n => n.position);
  // Measured, not estimated: every note is drawn already, placed or in the lane.
  const heightOf = n => document.querySelector(`.note[data-id="${n.id}"]`)?.offsetHeight ?? 160;
  // The wall stays as wide as the board shows at 100%: new columns go under
  // what is there instead of ever further right. Grown only sideways (each
  // column 352px right of the rightmost note), a session's wall made Fit
  // zoom out to 44% at 1920 by
  // 1080, where nothing on it could be read from the back of the room
  // (phase 5 review). The width leaves out the parked band laid over the
  // board's right edge and Fit's 40px margin on each side.
  const boardBox = $("board").getBoundingClientRect();
  const band = $("parked")?.hidden === false ? $("parked").getBoundingClientRect() : null;
  const covered = band && band.left > boardBox.left && band.left < boardBox.right ? boardBox.right - band.left : 0;
  const left = placed.length ? Math.min(...placed.map(n => n.position.x)) : 0;
  const top = placed.length ? Math.min(...placed.map(n => n.position.y)) : 0;
  // Column slots one widest note plus a gutter apart (320 + 64), as many as
  // fit that width; each new column goes into the slot whose lowest note is
  // highest, under that note, so the wall fills across before it grows down.
  const slots = Math.max(1, Math.floor((boardBox.width - covered - 2 * 40 + 64) / (320 + 64)));
  const boxes = placed.map(n => ({ x: n.position.x, bottom: n.position.y + heightOf(n) }));
  const slotBottom = k => {
    const x0 = left + k * (320 + 64);
    const under = boxes.filter(b => b.x < x0 + 320 && b.x + 320 > x0).map(b => b.bottom);
    return under.length ? Math.max(...under) + 64 : top;
  };
  const key = n => model.groupOf.get(n.id)?.id ?? n.data.refs?.[0]?.id ?? "typed";
  const columns = new Map();
  for (const n of todo) columns.set(key(n), [...(columns.get(key(n)) ?? []), n]);
  const placements = [];
  for (const notes of columns.values()) {
    let k = 0;
    for (let i = 1; i < slots; i++) if (slotBottom(i) < slotBottom(k)) k = i;
    const x = left + k * (320 + 64);
    let y = slotBottom(k);
    for (const n of notes) {
      placements.push({ id: n.id, x: Math.round(x), y: Math.round(y), expected_position_revision: 0 });
      y += heightOf(n) + 24;
    }
    boxes.push({ x, bottom: y - 24 });
  }
  for (let i = 0; i < placements.length; i += 50) {
    await send("item.place", { placements: placements.slice(i, i + 50), origin: "machine" });
  }
  app.board.view.touched = false;
}

// ----------------------------------------------------------------- composer

/** Add note, or for a facilitator, Add and accept (composer.mjs). One at a
 * time, so a double press cannot add the same words twice. */
async function addNote(accept) {
  const input = $("note-text");
  const text = input.value.trim();
  if (!text || app.adding) return;
  app.adding = true;
  try {
    if (!accept || app.snapshot?.session?.automatic_workspace) {
      let added;
      try { added = await send("source.text", { text }); }
      catch { return; }   // the banner already says why; nothing was added
      input.value = "";
      const automatic = app.snapshot?.session?.automatic_workspace;
      if (automatic && added?.proposal?.data?.item_id)
        app.undoStack.push({ id: added.proposal.data.item_id, text });
      attention(automatic ? "Added to the canvas." : "Added to the canvas, waiting for review.", "note");
      return;
    }
    app.batching = true;
    let outcome;
    try { outcome = await addAndAccept(send, text); }
    finally { app.batching = false; app.connection?.pollSoon?.(); }
    if (outcome.stage === "add") return;   // as above: nothing was added
    // Added, accepted or not: clearing the field stops a second press adding it again.
    input.value = "";
    if (outcome.item) {
      app.undoStack.push({ id: outcome.item.id, text: outcome.item.data?.text ?? text });
      app.lastAccepted = { id: outcome.item.id, text: outcome.item.data?.text ?? text };
    }
    const message = addAndAcceptMessage(outcome, describe);
    attention(message.text, message.kind);
    render();
  } finally {
    app.adding = false;
  }
}

// --------------------------------------------------------------------- undo

/** A canvas object a person erased (a stroke, a connector) goes on the undo
 * stack, so Undo in the bar puts it back: canvas.remove marks it undone and
 * keeps its record, and item.undo with the revision before the removal
 * restores it where it was (API.md, canvas objects). Only a facilitator may
 * send item.undo, so only a facilitator's removals are remembered. */
function rememberRemoval(payload, result) {
  const s = app.snapshot;
  const mine = s && me(s);
  if (mine?.role !== "facilitator" || !result?.item?.id) return;
  const before = s.records.find(r => r.id === payload.item_id);
  const kind = before?.data?.item_kind;
  const what = kind === "stroke" ? "the drawing" : kind === "arrow" ? "the connector" : "the erased object";
  app.undoStack.push({ id: result.item.id, restore: Number(payload.expected_revision), revision: Number(result.item.revision), text: what });
}

/** One step back from the last item this person accepted (F23). Undo never
 * rewinds the session: it marks the item undone, and its text stays in the
 * history. */
async function undo() {
  const last = app.undoStack.at(-1);
  if (!last) return;
  const item = app.snapshot.records.find(r => r.id === last.id);
  if (last.restore) {
    // An erased object: restore the revision it had before it was removed.
    // The removal's own answer gave its revision, so a press within a poll
    // of erasing works before this screen has heard of the removal. Changed
    // by someone since (a newer revision, no longer removed): nothing to do.
    if (item && item.revision > last.revision && item.data.status !== "undone") { app.undoStack.pop(); render(); return; }
    await send("item.undo", { item_id: last.id, expected_revision: Math.max(last.revision, item?.revision ?? 0), restore_revision: last.restore });
    app.undoStack.pop();
    attention(`Put back ${last.text}.`, "note");
    return;
  }
  if (!item || item.data.status !== "accepted") { app.undoStack.pop(); render(); return; }
  await send("item.undo", { item_id: item.id, expected_revision: item.revision, restore_revision: 0 });
  app.undoStack.pop();
  app.lastAccepted = null;
  attention(`Undid “${last.text.slice(0, 60)}”. It is no longer in the record.`, "note");
}

// ------------------------------------------------------------- selection

function onSelection(ids) {
  const s = app.snapshot;
  callTools("onSelection", ids);
  show($("selection"), ids.length > 0);
  if (!ids.length || !s) return;
  const model = boardModel(s);
  const notes = ids.map(id => model.notes.find(n => n.id === id)).filter(Boolean);
  const accepted = notes.filter(n => n.kind === "item");
  $("selection-count").textContent = `${ids.length} selected`;
  // A group holds accepted items only: the server refuses proposals, and a
  // group of guesses would be a claim built on claims.
  const groupable = accepted.length >= 2 && accepted.length === notes.length && accepted.every(n => !model.groupOf.has(n.id));
  $("propose-group").disabled = !groupable;
  show($("group-reason"), !groupable);
  $("group-reason").textContent = groupable ? "" : "Select two or more accepted notes that are not in a group yet.";
  $("ungroup").hidden = !notes.some(n => model.groupOf.has(n.id));
}

async function proposeGroup() {
  const model = boardModel(app.snapshot);
  const refs = [...app.board.selected].map(id => model.notes.find(n => n.id === id)).filter(Boolean)
    .map(n => ({ id: n.id, revision: n.revision }));
  const label = $("group-label").value.trim();
  if (!label) { attention("Name the group first, so the label says what it is about.", "note"); $("group-label").focus(); return; }
  await send("proposal.create", { proposal_kind: "relationship", form: "cluster", text: label, refs });
  $("group-label").value = "";
  app.board.select(null);
  attention(app.snapshot?.session?.automatic_workspace ? "Group added to the canvas." : "Group proposed. It is drawn dashed until a facilitator accepts it in Review.", "note");
}

async function ungroup() {
  const model = boardModel(app.snapshot);
  const byCluster = new Map();
  for (const id of app.board.selected) {
    const c = model.groupOf.get(id);
    if (c) byCluster.set(c, [...(byCluster.get(c) ?? []), id]);
  }
  for (const [c, ids] of byCluster) {
    await send("cluster.membership", { cluster_id: c.id, expected_revision: c.revision, remove: ids });
  }
  app.board.select(null);
}

// ------------------------------------------------------------------- listen

async function toggleListening() {
  if (app.mic) { stopListening(); return; }
  if (enrolmentAbort) { attention("Finish or cancel the voice recording first."); return; }
    wakeConfirmation.begin(app.snapshot);
    await wakeChime.unlock();
    wakeController = new WakewordController(app.client, {
      onState: state => { $("wakeword-status").textContent = `Wake-word detector: ${state}`; },
      onError: error => { $("wakeword-status").textContent = `Wake-word unavailable: ${error.message}. Transcript recognition still works.`; },
      onDetection: () => { $("wakeword-status").textContent = "Acoustic candidate; waiting for spoken activation confirmation."; },
    });
    if (app.snapshot.session.wakeword_available === false) {
      $("wakeword-status").textContent = "Acoustic detector unavailable: install the custom model. Transcript commands still work.";
    } else await wakeController.start();
  try {
    app.mic = await startCapture(app.client, {
      onFrame: frame => wakeController?.pushFrame(frame),
      onError: (error, chunk) => attention(
        `A ${Math.round(chunk.durationMs / 1000)} second piece of audio did not reach the server: ${describe(error)}`),
    });
    app.listenStarted = Date.now();
    tick();
    $("listen").textContent = "Stop listening";
    show($("listen-status"), true);
    rail("transcript");
  } catch (error) {
    stopListening();
    attention(error?.name === "NotAllowedError"
      ? "The browser was not allowed to use the microphone. Allow it in the address bar and try again."
      : `Could not start the microphone: ${describe(error)}`);
  }
}

function stopListening(reason) {
  const was = Boolean(app.mic);
  wakeController?.dispose(); wakeController = null;
  try { app.mic?.stop(); } catch {}
  app.mic = null;
  $("listen").textContent = "Listen";
  show($("listen-status"), false);
  if (was && reason) attention(reason, "note");
}

/** The recording timer: what the room needs to trust that "Recording" is true. */
function tick() {
  if (!app.mic) return;
  const s = Math.floor((Date.now() - app.listenStarted) / 1000);
  $("listen-timer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
setInterval(tick, 1000);

async function enrolSpeaker() {
  const name = $("speaker-name").value.trim();
  if (!name) { $("speaker-status").textContent = "Enter the speaker's name first."; return; }
  if (app.snapshot?.session.state !== "active" || enrolmentAbort) return;
  stopListening("Listening paused while a voice sample is recorded. Press Listen to continue.");
  const controller = new AbortController(); enrolmentAbort = controller;
  let submitted = false;
  $("speaker-enrol").disabled = true; show($("speaker-cancel"), true);
  $("speaker-status").textContent = "Preparing the microphone. Wait for the recording prompt.";
  try {
    const base64 = await recordVoiceSample({ signal: controller.signal, onReady: () => { $("speaker-status").textContent = "Recording for six seconds. Play or speak only this person’s voice now."; } });
    if (controller.signal.aborted || document.hidden || !navigator.onLine) return;
    $("speaker-status").textContent = "Storing the voice sample…";
    submitted = true;
    const result = await send("speaker.enroll", { name, mime: "audio/pcm16", base64, ended_reason: "silence" },
      { signal: controller.signal, timeoutMs: 45000 });
    $("speaker-status").textContent = result.profile.data.provenance.synthetic
      ? "Test profile stored. This server has no real speaker identifier enabled."
      : `${name} enrolled. Add another speaker, or press Listen to continue.`;
    $("speaker-name").value = "";
  } catch (error) {
    $("speaker-status").textContent = controller.signal.aborted
      ? submitted ? "Upload cancelled; the profile may have been stored. Check the enrolled list before trying again." : "Recording cancelled."
      : describe(error);
  } finally {
    if (enrolmentAbort === controller) enrolmentAbort = null;
    show($("speaker-cancel"), false);
    $("speaker-enrol").disabled = app.snapshot?.session.state !== "active";
  }
}

// ------------------------------------------------------------------- export

function renderExport(s) {
  const accepted = s.records.filter(r => r.kind === "item" && r.data.status === "accepted" && r.data.item_kind === "content").length;
  const waiting = s.records.filter(r => r.kind === "proposal" && ["needs_review", "stale"].includes(r.data.status)).length;
  $("export-summary").textContent = s.session.automatic_workspace ? `${accepted} notes on the canvas. ${waiting} unresolved source changes.` : waiting
    ? `${accepted} accepted ${accepted === 1 ? "note" : "notes"}. ${waiting} ${waiting === 1 ? "item was" : "items were"} never reviewed: leave them out, or include them marked as proposed.`
    : `${accepted} accepted ${accepted === 1 ? "note" : "notes"}, and nothing left unreviewed.`;
  $("export-retention").textContent = `Downloaded files are yours to keep. The session itself is deleted from the server on ${dateTime(s.session.expires)}.`;
}

/** The download links hold blob URLs, which count against the client's cap
 * of 16 media URLs; each export used to keep two for the life of the page. */
function clearExport() {
  const out = $("export-out");
  for (const link of out.querySelectorAll("a[href^='blob:']")) app.client?.revokeMediaUrl(link.href);
  out.textContent = "";
}

async function createExport() {
  const record = await send("export.create", { include_unresolved: $("include-unresolved").checked });
  const out = $("export-out");
  clearExport();
  for (const format of ["json", "markdown"]) {
    // Fetched with the session credential and offered as a file. A plain link
    // to the API would open without the credential and be refused.
    const body = await app.client.export(record.id, format);
    const blob = new Blob([format === "json" ? JSON.stringify(body, null, 2) : body],
      { type: format === "json" ? "application/json" : "text/markdown" });
    const link = document.createElement("a");
    link.className = "btn btn-secondary";
    link.href = app.client.createMediaUrl(blob);
    link.download = `${(app.snapshot.session.title || "session").replace(/[^\w-]+/g, "-")}.${format === "json" ? "json" : "md"}`;
    link.textContent = `Download ${format === "json" ? "JSON" : "Markdown"}`;
    out.append(link);
  }
}

// --------------------------------------------------------- end and delete

async function endSession() {
  const s = app.snapshot;
  const ok = await confirm({ title: "End this session?",
    text: "Capture stops for everyone and cannot start again in this session.",
    detail: `The canvas stays readable and can be exported until it is deleted on ${dateTime(s.session.expires)}.`,
    action: "End session" });
  if (!ok) return;
  stopListening();
  await send("session.close", { expected_session_revision: app.snapshot.session.revision });
}

async function deleteSession() {
  const ok = await confirm({ title: "Delete this session?",
    text: "Everything in it is removed from the server now: notes, photos, the transcript and voices.",
    detail: "Downloaded exports are not affected. This cannot be undone.", action: "Delete session" });
  if (!ok) return;
  try {
    stopListening();
    await app.client.delete();
    app.connection.dispose();
    app.snapshot = null;
    app.connection = null;
    show($("bar"), false);
    screen("setup");
    show($("start-join"), true);
    show($("page-head"), true);
    show($("consent"), false);
    attention("Deleted. The server keeps only a receipt that the session existed.", "note");
  } catch (error) { attention(describe(error)); }
}

// -------------------------------------------------------------------- start

async function connect(client) {
  app.client = client;
  app.connection = new SessionConnection(client, {
    pollIntervalMs: 1000,
    // Bound explicitly: bare `setTimeout` throws "Illegal invocation" in a
    // browser when called without `window` as its receiver.
    setTimeout: (fn, ms) => window.setTimeout(fn, ms),
    clearTimeout: id => window.clearTimeout(id),
    onUpdate: () => refresh(),
    onAttention: signal => {
      // Each of these switches the heartbeat off inside the library.
      if (HEARTBEAT_STOPPERS.has(signal.code) || signal.code.endsWith("heartbeat_requires_opt_in")) app.heartbeat = false;
      // The keep-alive banner says this in words, with the button to act on it.
      if (signal.code.endsWith("heartbeat_requires_opt_in")) { attention(""); render(); return; }
      if (signal.code === "hidden") return;
      if (signal.code === "control_uncertain" && uncertainBanner()) return;
      attention(CONNECTION_WORDS[signal.code] ?? `Connection problem: ${signal.code.replaceAll("_", " ")}.`);
    },
  });
  await app.connection.start();
  // A hidden tab or a lost network stops polling and heartbeats, and coming
  // back never restarts capture by itself.
  app.connection.setVisibility(document.visibilityState === "visible");
  app.connection.setOnline(navigator.onLine);
  await refresh();
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) { enrolmentAbort?.abort(); stopListening("Listening stopped because this tab was hidden. Press Listen to continue."); }
  app.connection?.setVisibility(document.visibilityState === "visible");
});
window.addEventListener("online", () => app.connection?.setOnline(true));
window.addEventListener("offline", () => { enrolmentAbort?.abort(); stopListening(); app.connection?.setOnline(false); });
window.addEventListener("pagehide", () => { enrolmentAbort?.abort(); stopListening(); });

const HEARTBEAT_STOPPERS = new Set(["hidden", "offline", "sync_failed", "heartbeat_failed", "control_uncertain", "control_conflict"]);

const CONNECTION_WORDS = {
  heartbeat_failed: "Could not keep capture running from this screen. It pauses itself within five minutes unless kept running.",
  control_conflict: "Someone changed the session at the same moment. Check what happened, then try again.",
  control_uncertain: "The server may or may not have applied that. Nothing was retried automatically.",
  control_reconciliation_abandoned: "Dropped the command whose outcome was unknown. Check the screen before doing it again.",
  offline: "You are offline. Nothing new arrives until the connection is back; capture on the server is unchanged.",
  sync_failed: "Could not refresh from the server. It keeps trying; what you see may be out of date.",
  session_deleted: "This session was deleted. The server keeps only a receipt.",
  // The credential stopped working. Before phase 4 these read "Connection
  // problem: client revoked." What is on screen stays, as the last thing
  // this device saw (DESIGN.md 4, next pass).
  client_revoked: "This device can no longer reach the session: it was deleted, or this person was removed. What is on screen is the last thing it saw.",
  client_expired: "This session has expired and was deleted from the server. What is on screen is the last thing this device saw.",
  client_deleted: "This session was deleted. What is on screen is the last thing this device saw.",
};

function screen(name) {
  app.screen = name;
  for (const id of ["setup", "workspace", "export"]) show($(`screen-${id}`), id === name);
  // The photograph sheet sits over the workspace only (photo.mjs owns it).
  if (name !== "workspace") photo.close();
  if (name === "workspace" && app.snapshot) requestAnimationFrame(() => render());
  if (name === "export" && app.snapshot) renderExport(app.snapshot);
  window.scrollTo({ top: 0 });
}

function rail(name) {
  app.rail = name;
  for (const id of ["review", "overview", "transcript", "people"]) show($(`rail-${id}`), id === name);
  for (const b of document.querySelectorAll("[data-rail]")) b.setAttribute("aria-selected", String(b.dataset.rail === name));
  if (name !== "review") app.focusProposal = null;
}

function setView(name) {
  app.view = name;
  for (const b of document.querySelectorAll("[data-view]")) b.setAttribute("aria-pressed", String(b.dataset.view === name));
  show($("board"), name === "canvas");
  show($("list-view"), name === "list");
  show($("calendar-view"), name === "calendar");
  show($("board-hint"), name === "canvas");
  show(document.querySelector(".zoom"), name === "canvas");
  render();
}

/** The projector setting (DESIGN.md 1.3): `data-projector` on <html> sets
 * --scale to 1.25, which grows every type size and nothing else. The board
 * is no longer zoomed with it. The stored key keeps its old name, so a
 * browser that had room view on comes back with the projector setting on. */
function setRoom(on) {
  const before = app.board?.roomZoom() ?? 1;
  if (on) document.documentElement.dataset.projector = ""; else delete document.documentElement.dataset.projector;
  // The canvas's type stays at one scale; the board's zoom carries the
  // projector there (board.mjs roomZoom). A view nobody has moved fits
  // again; a view a person chose keeps its place and grows or shrinks by
  // the same step as the type around it.
  if (app.board) {
    if (app.board.view.touched) app.board.zoomBy(app.board.roomZoom() / before); else app.board.fit();
  }
  $("room-toggle").setAttribute("aria-checked", String(on));
  $("room-toggle").textContent = on ? "Projector: on" : "Projector: off";
  try { localStorage.setItem("jarvaids-room", on ? "1" : ""); } catch {}
}

function toggleMenu(open) {
  const menu = $("session-menu");
  const next = open ?? menu.hidden;
  show(menu, next);
  $("session-menu-button").setAttribute("aria-expanded", String(next));
}

function serverUrl() {
  return $("base-url").value.trim() || "http://127.0.0.1:3000";
}

function wire() {
  app.board = new Board($("board"), {
    send,
    review: reviewFromBoard,
    attention,
    onSelection,
    onZoom: z => { $("zoom-level").textContent = `${Math.round(z * 100)}%`; callTools("onZoom", z); },
    crop: async (sourceId, revision, regionId) => {
      // Refused before asking, as the review rail does (review.mjs); the
      // board then says the photograph is not available to this person.
      if (!mayReadCrop(app.snapshot, sourceId)) throw new Error("Only the uploader and facilitators can see this crop.");
      return app.client.createMediaUrl(await app.client.crop(sourceId, revision, regionId));
    },
    revoke: url => app.client.revokeMediaUrl(url),
  });
  photo.wire();
  callTools("mount", ctx);

  for (const b of document.querySelectorAll("[data-rail]")) b.addEventListener("click", () => rail(b.dataset.rail));
  for (const b of document.querySelectorAll("[data-view]")) b.addEventListener("click", () => setView(b.dataset.view));
  $("zoom-in").addEventListener("click", () => app.board.zoomBy(1.2));
  $("zoom-out").addEventListener("click", () => app.board.zoomBy(1 / 1.2));
  $("zoom-fit").addEventListener("click", () => app.board.fit());
  $("topic-layout").addEventListener("click", () => { app.board.toggleLayout(); render(); });
  $("arrange").addEventListener("click", () => arrange().catch(() => {}));
  $("propose-group").addEventListener("click", () => proposeGroup().catch(() => {}));
  $("ungroup").addEventListener("click", () => ungroup().catch(() => {}));
  $("clear-selection").addEventListener("click", () => app.board.select(null));
  $("attention-dismiss").addEventListener("click", () => attention(""));
  $("attention-retry").addEventListener("click", () => retryControl());
  $("attention-discard").addEventListener("click", () => discardControl());

  const localApi = new URLSearchParams(location.search).get("api");
  if (localApi && /^http:\/\/127\.0\.0\.1:\d{1,5}$/.test(localApi)) $("base-url").value = localApi;
  $("session-timezone").value = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  $("create").addEventListener("click", async () => {
    try {
      const client = new GenAIClient({ baseUrl: serverUrl(), sessionId: newId(), token: newToken() });
      await client.create({ ownerName: $("owner-name").value.trim() || "Facilitator",
        title: $("session-title").value.trim() || "Session", timezone: $("session-timezone").value.trim() || "UTC", retentionSeconds: Number($("retention").value) });
      await connect(client);
    } catch (error) { attention(describe(error)); }
  });

  $("join").addEventListener("click", async () => {
    try {
      const code = splitJoinCode($("join-invitation").value.trim());
      const client = new GenAIClient({ baseUrl: serverUrl(), sessionId: code.sessionId, token: newToken() });
      // The joiner generates its own credential. The facilitator never holds
      // it, which is the whole point of the invitation flow.
      await client.join({ invitation: code.invitation,
        name: $("join-name").value.trim() || "Participant", policyVersion: code.policyVersion });
      await connect(client);
    } catch (error) { attention(describe(error)); }
  });

  $("agree-check").addEventListener("change", () => { $("acknowledge").disabled = !$("agree-check").checked; });
  $("acknowledge").addEventListener("click", () =>
    send("consent.acknowledge", { policy_version: app.snapshot.session.policy_version })
      .then(() => { $("agree-check").checked = false; }).catch(() => {}));
  // Starting or resuming capture is the facilitator's explicit choice to keep
  // it running, so the heartbeat comes on with it, once the update arrives.
  const activate = () => send("session.activate", { policy_version: app.snapshot.session.policy_version,
    expected_session_revision: app.snapshot.session.revision }).then(() => { app.wantHeartbeat = true; }).catch(() => {});
  $("activate").addEventListener("click", activate);
  $("resume").addEventListener("click", activate);
  $("stop-capture").addEventListener("click", () => { stopListening(); send("session.pause").catch(() => {}); });
  $("keep-alive").addEventListener("click", () => keepCaptureRunning());
  $("listen").addEventListener("click", () => toggleListening());
  $("undo").addEventListener("click", () => undo().catch(() => {}));
  $("speaker-enrol").addEventListener("click", () => enrolSpeaker());
  $("speaker-cancel").addEventListener("click", () => enrolmentAbort?.abort());
  $("bar-members").addEventListener("click", () => { if (app.screen !== "workspace") screen("workspace"); rail("people"); });

  $("composer").addEventListener("submit", event => { event.preventDefault(); addNote(false); });
  $("add-accept").addEventListener("click", () => addNote(true));

  $("make-invite").addEventListener("click", () => people.invite());
  $("copy-invite").addEventListener("click", () => people.copyInvite());

  $("session-menu-button").addEventListener("click", () => toggleMenu());
  // Only the Session menu's own wrap keeps it open: the Jarvaids menu beside it is another .menu-wrap (header.mjs).
  document.addEventListener("click", event => { if (!$("session-menu").parentElement.contains(event.target)) toggleMenu(false); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") toggleMenu(false); });
  $("room-toggle").addEventListener("click", () => { setRoom(!("projector" in document.documentElement.dataset)); toggleMenu(false); });
  $("open-export").addEventListener("click", () => { toggleMenu(false); clearExport(); screen("export"); });
  $("end-session").addEventListener("click", () => { toggleMenu(false); endSession().catch(() => {}); });
  $("delete-session").addEventListener("click", () => { toggleMenu(false); deleteSession(); });
  $("close-export").addEventListener("click", () => screen("workspace"));
  $("do-export").addEventListener("click", () => createExport().catch(error => attention(describe(error))));

  let room = false;
  try { room = localStorage.getItem("jarvaids-room") === "1"; } catch {}
  setRoom(room);
  $("summary-flush").addEventListener("click", () => send("summary.flush").catch(() => {}));
  $("summary-save").addEventListener("click", () => send("summary.configure", {
    agenda: $("summary-agenda").value.split("\n").map(v => v.trim()).filter(Boolean), enabled: $("summary-enabled").checked,
  }).catch(() => {}));
  rail("review");
  setView(app.view);
}

/**
 * A join code is `sessionId.policyVersion.invitation`.
 *
 * The server's invitation is only a credential: it does not carry the session
 * it belongs to, and joining needs the session id and the agreement version
 * the person is agreeing to. Rather than asking someone to type three things
 * off a projector, the facilitator's screen shows one string. A full stop is a
 * safe separator because neither a session id nor a credential can contain one.
 */
function splitJoinCode(code) {
  const parts = String(code).split(".");
  if (parts.length !== 3) {
    throw new RequestError("invalid_join_code");
  }
  const policyVersion = Number(parts[1]);
  if (!Number.isSafeInteger(policyVersion) || policyVersion < 1) {
    throw new RequestError("invalid_join_code");
  }
  return { sessionId: parts[0], policyVersion, invitation: parts[2] };
}
export { splitJoinCode, connect as connectSession };

wire();
