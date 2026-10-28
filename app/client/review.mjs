/**
 * The review panel: what is waiting, with its evidence first (F18, F19).
 *
 * A card is three things in a fixed order (DESIGN.md 1.3, "Review rail"):
 *   1. the evidence: the photograph crop the text was read from, the line
 *      "Typed by Jo" for a person's note, the member list of a proposed
 *      group, or a canvas proposal's list line;
 *   2. the text, in the Note style, which Correct turns into a field in place;
 *   3. the actions: Accept, Correct, Reject.
 * Evidence before text, because a reviewer who reads the claim first judges
 * the evidence against it instead of the other way round.
 *
 * A facilitator accepts or rejects; anyone else can save a correction, which
 * is kept as an edit for a facilitator to accept, never thrown away. A changed
 * field is a correction whether or not Correct was pressed, so typing into the
 * field and pressing Accept always sends `proposal.edit` first.
 *
 * Photo readings in progress or failed are listed above the queue, so a
 * reading never disappears silently (F16, F17).
 */
import { boardModel, machineMade, memberName, noteKind, readerName } from "./board.mjs";
import { canvasObject, objectLabel } from "./canvas-objects.mjs";
import { personIndex, personColour, clockTime } from "./people.mjs";

const JOB_WORDS = {
  capture_stopped: "Capture was paused before it finished.",
  deadline_exceeded: "It took longer than a minute.",
  adapter_timeout: "It took longer than a minute.",
  adapter_failed: "The reader could not read it.",
  interrupted_unknown_outcome: "The connection dropped while it was being read, so it may or may not have finished.",
  policy_changed: "The agreement changed before it finished.",
  source_changed: "The photograph's marks changed before it finished.",
  permission_changed: "The person who sent it can no longer add notes.",
  record_capacity: "The session holds as many notes as it can.",
  storage_capacity: "The session's storage is full.",
  user_cancelled: "It was cancelled.",
};

export function jobReason(job) {
  return JOB_WORDS[job.data.error] ?? "It could not be read.";
}

/** Notes a job will read: the regions of the photograph it refers to. */
export function jobSize(snapshot, job) {
  const source = snapshot.records.find(r => r.id === job.data.refs?.[0]?.id);
  return source?.data?.regions?.length ?? 0;
}

/** What kind of card a proposal makes. */
export function cardKind(p) {
  if (p.data.proposal_kind === "canvas") return "canvas";
  if (p.data.proposal_kind === "relationship" && p.data.form === "cluster") return "group";
  if (p.data.region_id) return "reading";
  return machineMade(p) ? "reading" : "typed";
}

/**
 * The card's actions, in the order they are drawn. Accept is always the first
 * primary button and Reject the first quiet one, because the journey and a
 * keyboard user both rely on that order. A canvas proposal has no Correct:
 * the server refuses to edit one ("reject it and propose again"), so offering
 * it would be a button that always fails.
 *
 *   facilitator, reading   accept, correct, reject
 *   ... while correcting   accept, discard, reject
 *   participant, author    correct, then save and discard while correcting
 *   participant, not       nothing: the server refuses proposal.edit from
 *                          anyone but the proposal's author or a facilitator
 *                          (service.py), so Correct would always fail. The
 *                          author of a reading is whoever sent the photograph.
 *   canvas                 accept, reject (facilitator); nothing otherwise
 */
export function cardActions({ facilitator, kind, correcting = false, author = true }) {
  if (kind === "canvas") return facilitator ? ["accept", "reject"] : [];
  if (facilitator) return ["accept", correcting ? "discard" : "correct", "reject"];
  if (!author) return [];
  return correcting ? ["save", "discard"] : ["correct"];
}

const ACTION_WORDS = {
  accept: ["Accept", "btn-primary"],
  correct: ["Correct", "btn-secondary"],
  discard: ["Keep original", "btn-secondary"],
  reject: ["Reject", "btn-quiet"],
  save: ["Save correction", "btn-secondary"],
};

/** A proposal's text has been corrected once a person edited it: the server
 * records the editor only on `proposal.edit`. */
export function wasCorrected(p) {
  return Boolean(p.data.last_editor);
}

/** Drawn as proposed: anything a person did not write (the server marks it
 * `fixture` or `model`, never `human`), a proposed group and every canvas
 * proposal. A person's own typed note is not: it still needs review, but it
 * is no guess, so its marker says "not yet reviewed". */
export function drawnProposed(p) {
  const kind = cardKind(p);
  return kind === "group" || kind === "canvas" || machineMade(p);
}

/** Whether this person may see a photograph's crops: a facilitator, or the
 * participant who uploaded it (the server's rule, service.py, crop
 * evidence). Asking anyway is refused with a 403, which a participant's
 * console shows as an error for every card; the answer is known from the
 * snapshot, so the client does not ask. */
export function mayReadCrop(snapshot, sourceId) {
  const me = snapshot?.members?.find(m => m.id === snapshot.actor_id);
  if (!me) return false;
  if (me.role === "facilitator") return true;
  const source = snapshot.records?.find(r => r.id === sourceId);
  return me.role === "participant" && Boolean(source) && source.data?.author_id === me.id;
}

export function createReview(ctx) {
  const { app, $, show, send, attention, render, button, confirm } = ctx;
  // Cards whose text is open as a field. Kept across renders, because the
  // queue is redrawn on every poll and a half-made correction must survive.
  const correcting = new Set();

  wireTabKeys();

  /** A crop is fetched once per proposal and kept as a blob URL. */
  function cropFor(p) {
    const source = p.data.refs?.[0];
    if (!p.data.region_id || !source) return null;
    const key = `${p.id}:${source.revision}`;
    if (app.crops.has(key)) return app.crops.get(key);
    if (!mayReadCrop(app.snapshot, source.id)) { app.crops.set(key, false); return false; }
    app.crops.set(key, null);
    app.client.crop(source.id, source.revision, p.data.region_id)
      .then(blob => { app.crops.set(key, app.client.createMediaUrl(blob)); render(); })
      .catch(() => { app.crops.set(key, false); render(); });
    return null;
  }

  /** A card that left the queue (accepted, rejected, gone) gives its crop's
   * blob URL back. The client holds at most 16 media URLs (client.mjs), and
   * before phase 4 none was ever released, so a long session's seventeenth
   * crop failed and said, wrongly, that the photograph was not visible to
   * this person (DESIGN.md 0.3 and 1.4). A refused crop (false) is
   * forgotten too, so a card that comes back asks again. */
  function releaseCrops(open) {
    for (const [key, url] of app.crops) {
      const id = key.slice(0, key.lastIndexOf(":"));
      if (open.has(id)) continue;
      if (typeof url === "string") app.client?.revokeMediaUrl(url);
      // null is a fetch still in flight; its answer is released when it lands.
      if (url !== null) app.crops.delete(key);
    }
  }

  function confidence(p) {
    if (!("confidence" in p.data)) return "";
    return p.data.confidence == null ? "Confidence not measured" : `Confidence ${Math.round(p.data.confidence * 100)}%`;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /** A small circle in a person's colour, the same mark People and the
   * transcript use, so a reviewer can see whose note it is at a glance. */
  function personDot(s, actorId) {
    const dot = el("span", "person-dot person-dot-sm");
    dot.setAttribute("aria-hidden", "true");
    const index = personIndex(s, actorId);
    if (index >= 0) dot.style.setProperty("--person", personColour(index));
    else dot.classList.add("person-dot-none");
    return dot;
  }

  /** 1. The evidence. */
  function evidence(s, p, kind) {
    if (p.data.summary_batch_id) {
      const line = el("p", "evidence evidence-line t-body", "Created from the supplied brainstorm summary");
      if (p.data.summary_detail && p.data.summary_detail !== p.data.text)
        line.title = p.data.summary_detail;
      return line;
    }
    if (kind === "group") {
      const members = el("ul", "evidence evidence-members members t-small");
      members.setAttribute("aria-label", "Notes in this group");
      for (const ref of p.data.refs ?? []) {
        members.append(el("li", "", s.records.find(r => r.id === ref.id)?.data.text ?? "A note that is no longer on the canvas"));
      }
      return members;
    }
    if (kind === "canvas") {
      const obj = canvasObject(p);
      return el("p", "evidence evidence-line t-body", obj ? objectLabel(obj, boardModel(s).nameOf) : "A canvas object");
    }
    if (p.data.region_id) {
      const figure = el("figure", "evidence evidence-crop");
      figure.dataset.regionId = p.data.region_id;
      if (p.data.refs?.[0]) figure.dataset.sourceId = p.data.refs[0].id;
      const crop = cropFor(p);
      if (crop) {
        const img = el("img", "crop-img");
        img.src = crop;
        img.alt = "The part of the photograph this was read from";
        figure.append(img);
      } else {
        figure.append(el("div", "crop-placeholder t-small", crop === false
          ? "The photograph is only visible to the person who took it and to facilitators."
          : "Loading the part of the photograph…"));
      }
      if (crop) figure.append(el("figcaption", "t-small crop-caption", [noteKind(p), confidence(p)].filter(Boolean).join(". ")));
      return figure;
    }
    // A typed note's evidence is the person who typed it, and when.
    const line = el("p", "evidence evidence-typed t-body");
    line.append(personDot(s, p.data.author_id), el("span", "", `Typed by ${memberName(s, p.data.author_id)}`));
    if (p.data.created_at) line.append(el("time", "t-mono", clockTime(p.data.created_at)));
    return line;
  }

  /** The mono marker and the origin line, under the text. */
  function metaLine(s, p, kind) {
    const meta = el("p", "proposal-meta");
    const proposed = drawnProposed(p);
    const marker = el("span", "badge proposal-marker " + (proposed ? "st-provisional" : "st-off"),
      proposed ? "proposed" : "not yet reviewed");
    const origin = el("span", "origin t-small");
    origin.textContent = kind === "group" ? `Group proposed by ${memberName(s, p.data.author_id)}, not yet accepted`
      : kind === "canvas" ? `Proposed by ${machineMade(p) ? readerName(p.data) : memberName(s, p.data.author_id)}, not yet accepted`
      : kind === "reading" && machineMade(p) ? readingLabel(p.data)
      : kind === "reading" ? `Retyped by ${memberName(s, p.data.author_id)}, not yet accepted`
      : "Not yet accepted. A person's own note still goes through review";
    if (p.data.status === "stale") origin.textContent += ". Its source changed since this was made";
    meta.append(marker, origin);
    return meta;
  }

  function renderJobs(s) {
    const box = $("jobs");
    box.textContent = "";
    const jobs = s.records.filter(r => r.kind === "job").sort((a, b) => (b.data.created_at ?? 0) - (a.data.created_at ?? 0));
    for (const job of jobs) {
      const status = job.data.status;
      if (status === "succeeded" || app.dismissedJobs.has(job.id)) continue;
      const n = jobSize(s, job);
      const done = ["failed", "cancelled"].includes(status);
      const row = el("div", "job" + (done ? " job-done" : ""));
      row.dataset.id = job.id;
      const mark = el("span", "status " + (done ? "st-failed" : "st-waiting"));
      mark.innerHTML = `<i class="glyph ${done ? "glyph-failed" : "glyph-waiting"}" aria-hidden="true"></i>`;
      mark.append(el("span", "word", status === "queued" ? `Waiting to read ${n} ${n === 1 ? "note" : "notes"}`
        : status === "running" ? `Reading ${n} ${n === 1 ? "note" : "notes"}`
        : status === "cancelled" ? "Reading cancelled" : "Reading failed"));
      row.append(mark);
      if (job.data.created_at) row.append(el("time", "t-mono job-time", clockTime(job.data.created_at)));
      if (done) {
        const actions = el("div", "job-actions");
        actions.append(button("Try again", "btn-secondary btn-sm", () => retry(s, job)),
          button("Dismiss", "btn-quiet btn-sm", async () => { app.dismissedJobs.add(job.id); render(); }));
        row.append(el("p", "t-small job-reason", jobReason(job)), actions);
      }
      box.append(row);
    }
  }

  /** A failed or cancelled reading is queued again. When the first attempt's
   * outcome is unknown, the server asks for an explicit "it may cost again". */
  async function retry(s, job) {
    const source = s.records.find(r => r.id === job.data.refs?.[0]?.id);
    if (!source) { attention("The photograph is no longer in the session."); return; }
    try {
      await send("extraction.queue", { source_id: source.id, expected_revision: source.revision });
    } catch (error) {
      const code = error?.code ?? error?.cause?.code;
      if (code !== "uncertain_retry_requires_acknowledgement") return;
      const ok = await confirm({
        title: "Read this photograph again?",
        text: "The last attempt may have finished, or the connection dropped before we heard back. Reading it again may be charged again.",
        detail: "The notes from both attempts would need review, so check the queue first.",
        action: "Read again", danger: false,
      });
      if (!ok) return;
      await send("extraction.queue", { source_id: source.id, expected_revision: source.revision,
        retry_of: error.details?.retry_of ?? job.id, acknowledge_uncertain_cost: true });
    }
    app.dismissedJobs.add(job.id);
  }

  function renderUndoLine() {
    const line = $("undo-line");
    const last = app.undoStack.at(-1);
    show(line, Boolean(app.lastAccepted && last && last.id === app.lastAccepted.id));
    if (line.hidden) return;
    line.textContent = "";
    line.append(el("span", "t-small", `Accepted “${app.lastAccepted.text.slice(0, 60)}${app.lastAccepted.text.length > 60 ? "…" : ""}”.`),
      button("Undo", "btn-quiet btn-sm", () => ctx.undo()));
  }

  /** What had focus inside the queue, so a redraw on the next poll puts it
   * back: a keyboard user must not be thrown out of a card every second. */
  function focusKey() {
    const active = document.activeElement;
    const card = active?.closest?.(".proposal[data-id]");
    if (!card) return null;
    if (active.dataset.draftFor) return { id: card.dataset.id, field: true, caret: active.selectionStart };
    if (active.dataset.action) return { id: card.dataset.id, action: active.dataset.action };
    return null;
  }

  function restoreFocus(key) {
    if (!key) return;
    const card = document.querySelector(`.proposal[data-id="${CSS.escape(key.id)}"]`);
    if (!card) return;
    if (key.field) {
      const field = card.querySelector("textarea");
      if (!field || field.closest("[hidden]")) return;
      field.focus();
      const at = Math.min(key.caret ?? field.value.length, field.value.length);
      field.setSelectionRange(at, at);
      return;
    }
    // Correct and Discard swap places, so the button that replaced the one
    // pressed takes the focus.
    const swap = { correct: "discard", discard: "correct", save: "correct" };
    (card.querySelector(`[data-action="${key.action}"]`) ?? card.querySelector(`[data-action="${swap[key.action]}"]`))?.focus();
  }

  function renderQueue(s, proposals) {
    renderJobs(s);
    renderUndoLine();
    const box = $("queue");
    const keep = focusKey();
    box.textContent = "";
    show($("queue-empty"), proposals.length === 0);
    const open = new Set(proposals.map(p => p.id));
    for (const id of correcting) if (!open.has(id)) correcting.delete(id);
    releaseCrops(open);
    const mine = s.members.find(m => m.id === s.actor_id);
    const facilitator = mine?.role === "facilitator";
    for (const p of proposals) box.append(card(s, p, facilitator));
    restoreFocus(keep);
  }

  function card(s, p, facilitator) {
    const kind = cardKind(p);
    const row = el("article", "proposal proposal-" + kind + (drawnProposed(p) ? " provisional" : ""));
    row.dataset.id = p.id;
    row.setAttribute("aria-label", kind === "group" ? "Proposed group" : kind === "canvas" ? "Proposed canvas object"
      : kind === "typed" ? "Typed note, not yet reviewed" : "Proposed reading");
    if (app.focusProposal === p.id) row.classList.add("focused");

    // 1. Evidence.
    row.append(evidence(s, p, kind));
    if (kind === "canvas") {
      row.append(metaLine(s, p, kind), actionsFor(s, p, kind, facilitator, null));
      if (!facilitator) row.append(el("p", "t-small why", "A facilitator accepts or rejects."));
      return row;
    }

    // 2. The text, and the field Correct opens in its place.
    const unreadable = p.data.reading_status === "unreadable";
    // Only the proposal's author or a facilitator may correct it.
    const author = p.data.author_id === s.actor_id;
    const mayEdit = facilitator || author;
    const draft = app.drafts.get(p.id);
    const value = draft && draft.revision === p.revision ? draft.text : p.data.text ?? "";
    // Opening a card from the canvas ("Review" on a note) means reviewing it
    // now, so its field opens with it; so does a card with an unsaved draft,
    // and a reading nobody could read, which has nothing to show but a field.
    if (mayEdit && (app.focusProposal === p.id || unreadable || value !== (p.data.text ?? ""))) correcting.add(p.id);
    const isCorrecting = correcting.has(p.id);

    const text = el("p", "proposal-text t-note", p.data.text || "");
    if (wasCorrected(p)) text.classList.add("corrected");
    text.hidden = isCorrecting || !p.data.text;

    const label = kind === "group" ? "Name of the group" : "The text, corrected if needed";
    const field = el("textarea", "proposal-field t-note" + (wasCorrected(p) || value !== (p.data.text ?? "") ? " corrected" : ""));
    field.rows = 2;
    field.value = value;
    field.dataset.draftFor = p.id;
    field.setAttribute("aria-label", label);
    const fieldWrap = el("div", "proposal-correct");
    fieldWrap.hidden = !isCorrecting;
    if (unreadable) {
      const tag = el("span", "status st-failed");
      tag.innerHTML = '<i class="glyph glyph-failed" aria-hidden="true"></i><span class="word">Unreadable: type what the note says</span>';
      fieldWrap.append(tag);
    }
    fieldWrap.append(field);
    row.append(text, fieldWrap, metaLine(s, p, kind));

    const actions = actionsFor(s, p, kind, facilitator, field, isCorrecting, author);
    row.append(actions);
    if (!facilitator) row.append(el("p", "t-small why", author
      ? "A facilitator accepts or rejects. Your correction is kept."
      : "A facilitator accepts or rejects. Only a facilitator or the person who added it can correct it."));

    field.addEventListener("input", () => {
      app.drafts.set(p.id, { revision: p.revision, text: field.value });
      field.classList.toggle("corrected", wasCorrected(p) || field.value !== (p.data.text ?? ""));
      const accept = actions.querySelector('[data-action="accept"]');
      if (accept) accept.disabled = !field.value.trim();
    });
    field.addEventListener("keydown", event => {
      if (event.key === "Escape" && field.value === (p.data.text ?? "") && !unreadable) {
        event.stopPropagation();
        discard(p);
      }
    });
    return row;
  }

  function discard(p) {
    app.drafts.delete(p.id);
    correcting.delete(p.id);
    if (app.focusProposal === p.id) app.focusProposal = null;
    render();
    document.querySelector(`.proposal[data-id="${CSS.escape(p.id)}"] [data-action="correct"]`)?.focus();
  }

  function actionsFor(s, p, kind, facilitator, field, isCorrecting = false, author = true) {
    const actions = el("div", "row proposal-actions");
    const accepted = (item, text) => {
      if (!item) return;
      app.undoStack.push({ id: item.id, text: item.data?.text ?? text });
      app.lastAccepted = { id: item.id, text: item.data?.text ?? text };
      render();
    };
    const handlers = {
      accept: async () => {
        if (kind === "canvas") {
          const label = objectLabel(canvasObject(p) ?? { kind: "object", fields: {} }, boardModel(s).nameOf);
          const result = await send("proposal.review", { proposal_id: p.id, expected_revision: p.revision, decision: "accept" });
          accepted(result?.item, label);
          return;
        }
        // Correcting before accepting is the normal path, not an exception:
        // a changed field is sent as the correction, then the review.
        let current = p;
        if (field.value !== (p.data.text ?? "")) {
          current = await send("proposal.edit", { proposal_id: p.id,
            expected_revision: p.revision, text: field.value, refs: p.data.refs });
        }
        const result = await send("proposal.review", { proposal_id: current?.id ?? p.id,
          expected_revision: current?.revision ?? p.revision, decision: "accept" });
        app.drafts.delete(p.id);
        correcting.delete(p.id);
        accepted(result?.item, field.value);
      },
      correct: async () => {
        correcting.add(p.id);
        render();
        const open = document.querySelector(`.proposal[data-id="${CSS.escape(p.id)}"] textarea`);
        if (open) { open.focus(); open.setSelectionRange(open.value.length, open.value.length); }
      },
      discard: async () => discard(p),
      reject: async () => {
        await send("proposal.review", { proposal_id: p.id, expected_revision: p.revision, decision: "reject" });
        app.drafts.delete(p.id);
        correcting.delete(p.id);
      },
      // A participant's correction is saved as an edit a facilitator then
      // accepts. Before, the field looked editable and the edit was lost.
      save: async () => {
        if (field.value === (p.data.text ?? "")) { discard(p); return; }
        await send("proposal.edit", { proposal_id: p.id, expected_revision: p.revision, text: field.value, refs: p.data.refs });
        app.drafts.delete(p.id);
        correcting.delete(p.id);
        attention("Correction saved. A facilitator accepts it into the record.", "note");
      },
    };
    for (const name of cardActions({ facilitator, kind, correcting: isCorrecting, author })) {
      const [label, variant] = ACTION_WORDS[name];
      const b = button(kind === "group" && name === "accept" ? "Accept group" : label, variant, handlers[name]);
      b.dataset.action = name;
      if (name === "accept" && field) b.disabled = !field.value.trim();
      actions.append(b);
    }
    return actions;
  }

  return { renderQueue, cropFor, confidence };
}

/** Left and right arrows move between the rail's tabs, as a tab list does.
 * app.mjs wires the clicks; this only moves the focus and presses. */
function wireTabKeys() {
  const list = typeof document !== "undefined" && document.querySelector(".ws-rail [role=tablist]");
  if (!list || list.dataset.keys) return;
  list.dataset.keys = "1";
  list.addEventListener("keydown", event => {
    const tabs = [...list.querySelectorAll("[role=tab]")].filter(tab => !tab.hidden);
    const at = tabs.indexOf(document.activeElement);
    if (at < 0) return;
    const to = event.key === "ArrowRight" ? (at + 1) % tabs.length
      : event.key === "ArrowLeft" ? (at - 1 + tabs.length) % tabs.length
      : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    if (to < 0) return;
    event.preventDefault();
    tabs[to].focus();
    tabs[to].click();
  });
}

/** Names the reader, and says so when the reading is a stand-in, because a
 * label that hides `synthetic` would present a fixture as a reading. */
export function readingLabel(data) {
  if (data.synthetic) return "Stand-in reading (fixture): no handwriting recognition ran. Not yet accepted";
  return `Read by ${readerName(data)}, not yet accepted`;
}
