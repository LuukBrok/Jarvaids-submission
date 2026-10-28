import { commandFeedback } from "../server/voice-command-feedback.mjs";
import { sentenceRows } from "./transcript-sentences.mjs";
import { memberName } from "./board.mjs";
import { personIndex, personColour, personInk, clockTime } from "./people.mjs";

/**
 * The transcript: who said what, when, in the rail (F09, F10).
 *
 * Each row is one displayed sentence: a mono time, the speaker in their
 * People colour, a badge, the words. The newest row is the current line, on
 * the highlight tone. A recognised voice command is its own kind of row, on
 * the periwinkle tone, with what was asked and what happened to it, because a
 * command heard is not a command done and the room should see both.
 *
 * Every row can be quoted onto the canvas. The rail does not make the note:
 * pressing Quote dispatches `jv:quote` on document with the line's words and
 * where they came from, and the quote tool (tools/quote.mjs) listens.
 *
 * Contracts other tools rely on:
 *   row      .transcript-row[data-segment-id="<id>"]#seg-<id>, where <id> is
 *            the segment's record id, or the first segment's id for a
 *            sentence joined from several
 *   button   .quote-line inside the row
 *   event    jv:quote, detail {segmentId, text, speakerName, speakerActorId,
 *            createdAt}; see quoteDetail
 *   class    .quoted-highlight on a row draws it on the highlight tone; it is
 *            the quote tool's to add and remove, and it survives a redraw
 *
 * Server recognition metadata is shown beside the original words. The client
 * does not infer commands or treat recognition as approval to execute them.
 */

/** Who a segment is attributed to, and how sure that is.
 *    voice_identified   the enrolled voice's name; a member only if a member
 *                       has that name, because the profile is not a member
 *    unidentified       "Unknown speaker", nobody
 *    otherwise          the member whose device sent the audio */
export function speakerOf(snapshot, data) {
  if (data.attribution === "unidentified") return { name: "Unknown speaker", actorId: null, unknown: true };
  if (data.attribution === "voice_identified") {
    const match = snapshot?.members?.find(m => m.name?.trim().toLowerCase() === data.speaker_name?.trim().toLowerCase());
    return { name: data.speaker_name || "Unknown speaker", actorId: match?.id ?? null, unknown: !data.speaker_name, matched: true };
  }
  return { name: memberName(snapshot, data.speaker_actor_id), actorId: data.speaker_actor_id ?? null, unknown: false };
}

/** The words a row shows: the corrected activation phrase when there is one. */
export function rowWords(data) {
  const correction = !data.provenance?.synthetic && data.activation_correction?.corrected ? data.activation_correction : null;
  return correction?.text ?? data.display_text ?? data.text ?? "";
}

/** The `jv:quote` event detail for one displayed row (a sentenceRows row).
 * segmentId is the first segment's record id; createdAt is the record's
 * `created_at`, seconds since 1970; speakerActorId is the member the colour
 * comes from, or null when nobody is known (an unknown or unmatched voice). */
export function quoteDetail(snapshot, row) {
  const speaker = speakerOf(snapshot, row.data);
  return {
    segmentId: row.segment_ids?.[0] ?? row.id ?? null,
    text: rowWords(row.data),
    speakerName: speaker.name,
    speakerActorId: speaker.actorId,
    createdAt: row.data.created_at ?? null,
  };
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// What the last render drew, so a poll that brings nothing new leaves the
// rows alone: an open disclosure, a hovered Quote button and the keyboard
// focus stay where they are.
let drawn = "";

export function renderTranscript(snapshot) {
  const segments = snapshot.records.filter(r => r.kind === "transcript_segment" &&
      r.data.status === "final" && r.data.text?.trim())
    .sort((a, b) => (a.data.created_at ?? 0) - (b.data.created_at ?? 0));
  const box = document.getElementById("transcript");
  const voiceMatching = snapshot.records.some(r => r.kind === "speaker_profile") ||
    segments.some(r => ["voice_identified", "unidentified"].includes(r.data.attribution));
  const synthetic = segments.some(r => r.data.provenance?.synthetic);
  const failed = snapshot.records.some(r => r.kind === "transcript_segment" &&
      r.data.failure_reason === "transcription_failed");
  const note = document.getElementById("transcript-note");
  const noteText = failed
    ? "Some audio could not be transcribed because of a technical error. Listening continues."
    : !segments.length ? "Recognised speech will appear here while listening."
    : synthetic ? "Stand-in transcript: no speech recognition ran. Speakers are whoever's device sent the audio."
    : voiceMatching ? "Enrolled voices are matched automatically. Uncertain matches appear as Unknown speaker."
    : "Speakers are whoever's device sent the audio, not voice recognition.";
  if (note.textContent !== noteText) note.textContent = noteText;
  note.classList.toggle("transcript-failed", failed);

  const rows = sentenceRows(segments);
  const signature = JSON.stringify([rows.map(r => [r.segment_ids, r.data.text, r.data.display_text, r.data.attribution,
    r.data.speaker_name, r.data.speaker_actor_id, r.data.voice_command, r.data.activation_correction, r.data.created_at]),
    (snapshot.members ?? []).map(m => [m.id, m.name]), snapshot.session?.automatic_workspace,
    snapshot.records.filter(r => ["poll","command_document"].includes(r.kind)).map(r => [r.id,r.data.state])]);
  let latest = null;
  for (const row of rows) {
    const heard = row.data.provenance?.synthetic ? null : row.data.voice_command;
    if (heard) {
      const poll = snapshot.records.find(r => r.kind === "poll" && row.segment_ids.includes(r.data.command_source_id)) ||
        (heard.poll_action ? snapshot.records.filter(r => r.kind === "poll").at(-1) : null);
      const doc = snapshot.records.filter(r => r.kind === "command_document" && r.data.document_type === (heard.intent === "planning" ? "calendar" : heard.intent)).at(-1);
      latest = commandFeedback(heard, poll?.data.state, doc?.data.state, snapshot.session?.automatic_workspace, snapshot.session?.summary_ai?.available);
    }
  }
  const indicator = document.getElementById("command-status");
  indicator.hidden = !latest;
  // Polling can render the same snapshot repeatedly. Change the live region
  // only when its message changes, so screen readers do not repeat it.
  if (indicator.textContent !== (latest ?? "")) indicator.textContent = latest ?? "";
  if (signature === drawn && box.childElementCount === rows.length) return;
  drawn = signature;

  const atEnd = box.scrollTop + box.clientHeight >= box.scrollHeight - 8;
  const focused = document.activeElement?.closest?.("#transcript .transcript-row")?.dataset.segmentId;
  const open = new Set([...box.querySelectorAll(".transcript-row")]
    .filter(r => r.querySelector(".activation-correction[open]")).map(r => r.dataset.segmentId));
  const quoted = new Set([...box.querySelectorAll(".transcript-row.quoted-highlight")].map(r => r.dataset.segmentId));
  box.textContent = "";
  rows.forEach((segment, i) => box.append(transcriptRow(snapshot, segment, {
    current: i === rows.length - 1, open, quoted })));
  if (focused) box.querySelector(`.transcript-row[data-segment-id="${CSS.escape(focused)}"] .quote-line`)?.focus({ preventScroll: true });
  if (atEnd) box.scrollTop = box.scrollHeight;
}

function transcriptRow(snapshot, segment, { current, open, quoted }) {
  const data = segment.data;
  const heard = data.provenance?.synthetic ? null : data.voice_command;
  const poll = snapshot.records.filter(r => r.kind === "poll").at(-1);
  const doc = snapshot.records.filter(r => r.kind === "command_document" && r.data.document_type === (heard?.intent === "planning" ? "calendar" : heard?.intent)).at(-1);
  const feedback = heard ? commandFeedback(heard, poll?.data.state, doc?.data.state, snapshot.session?.automatic_workspace, snapshot.session?.summary_ai?.available) : null;
  const recognised = heard?.status === "recognised";
  const detail = quoteDetail(snapshot, segment);

  const row = el("div", "jv-row transcript-row");
  if (detail.segmentId) {
    row.dataset.segmentId = detail.segmentId;
    row.id = `seg-${detail.segmentId}`;
  }
  if (recognised) row.classList.add("transcript-command");
  if (current) { row.classList.add("transcript-current"); row.setAttribute("aria-current", "true"); }
  if (detail.segmentId && quoted.has(detail.segmentId)) row.classList.add("quoted-highlight");

  const head = el("div", "transcript-head");
  const time = el("time", "t-mono transcript-time", clockTime(data.created_at, { withSeconds: true }));
  if (data.created_at != null) time.dateTime = new Date(data.created_at * 1000).toISOString();

  const speaker = speakerOf(snapshot, data);
  const index = personIndex(snapshot, speaker.actorId);
  const who = el("span", "transcript-speaker", speaker.name);
  if (speaker.unknown) who.classList.add("speaker-unknown");
  if (index >= 0) {
    who.style.setProperty("--speaker-ink", personInk(index));
    who.style.setProperty("--person", personColour(index));
    who.classList.add("speaker-known");
  }
  if (data.attribution === "voice_identified") who.title = "Automatic voice match; may be incorrect.";

  // An ordinary line's badge is for a screen reader only: on screen every
  // row is transcript, and the badge earns its place only for a command.
  const badge = el("span", "t-small transcript-badge" + (heard ? "" : " visually-hidden"), "Transcript");
  if (heard) {
    badge.textContent = recognised ? (snapshot.session?.automatic_workspace ? "Command" : "Provisional command")
      : heard.status === "incomplete" ? "Request unfinished" : "Command not recognised";
    if (recognised) {
      // Heard, not done: a recognised command is proposed until it runs.
      badge.classList.add("status", "command-provisional");
      const glyph = el("i", "glyph glyph-provisional");
      glyph.setAttribute("aria-hidden", "true");
      badge.prepend(glyph);
    } else {
      badge.classList.add("command-other");
    }
  }

  const quote = el("button", "btn btn-quiet btn-sm quote-line", "Quote");
  quote.type = "button";
  const at = clockTime(data.created_at);
  quote.setAttribute("aria-label", `Quote ${speaker.name}${at ? ` at ${at}` : ""} onto the canvas`);
  quote.addEventListener("click", () => {
    document.dispatchEvent(new CustomEvent("jv:quote", { detail: quoteDetail(snapshot, segment) }));
  });
  head.append(time, who, badge, quote);

  const words = el("p", "t-body transcript-words", rowWords(data));
  row.append(head, words);

  const correction = !data.provenance?.synthetic && data.activation_correction?.corrected;
  if (correction) {
    const details = el("details", "t-small activation-correction");
    if (detail.segmentId && open.has(detail.segmentId)) details.open = true;
    details.append(el("summary", "", "Activation phrase corrected"),
      el("span", "", `Whisper originally heard: ${data.text}`));
    row.append(details);
  }
  if (heard) row.append(el("p", "t-small command-feedback", feedback));
  return row;
}
