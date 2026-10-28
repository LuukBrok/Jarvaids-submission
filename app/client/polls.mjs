/** Views of server-owned polls. AI output never supplies vote totals. */
export function pollModel(snapshot, poll) {
  const records = snapshot?.records ?? [];
  const profiles = records.filter(r => r.kind === "speaker_profile");
  const ballots = records.filter(r => r.kind === "poll_ballot" && r.data.poll_id === poll.id);
  const work = records.filter(r => r.kind === "poll_work" && r.data.poll_id === poll.id);
  const bySpeaker = new Map(ballots.map(b => [b.data.speaker_profile_id, b]));
  const options = poll.data.options.map(o => ({ ...o,
    voters: profiles.filter(p => bySpeaker.get(p.id)?.data.option_id === o.id) }));
  const voted = options.reduce((n, o) => n + o.voters.length, 0);
  return { profiles, ballots, options, voted, notVoted: profiles.length - voted,
    pending: work.filter(w => ["queued", "running"].includes(w.data.status)),
    unresolved: work.filter(w => ["clarify", "error", "uncertain"].includes(w.data.status)) };
}

/** The tally as bars: each choice's count, share and voters, and which choice
 * has the most votes. A tie is a tie: every choice level at the top is marked
 * as tied and none is called the winner. Nothing is marked before a vote. */
export function pollTally(model) {
  const top = Math.max(0, ...model.options.map(o => o.voters.length));
  const leaders = top ? model.options.filter(o => o.voters.length === top).map(o => o.id) : [];
  const outcome = !leaders.length ? "none" : leaders.length === 1 ? "lead" : "tie";
  return { outcome, leaders, rows: model.options.map((o, i) => ({ id: o.id, letter: String.fromCharCode(65 + i), label: o.label,
    count: o.voters.length, share: model.voted ? o.voters.length / model.voted : 0, names: o.voters.map(p => p.data.name),
    mark: !leaders.includes(o.id) ? "" : outcome === "tie" ? "tie" : "lead" })) };
}

/** The words on a marked bar. While voting is open the top choice is only
 * leading; once voting stops it has the most votes. Neither says "agreed". */
export function tallyMark(mark, state) {
  if (!mark || state === "cancelled") return "";
  if (mark === "tie") return "Tie";
  if (mark === "lead") return state === "open" ? "Leading" : "Most votes";
  return "";
}

const STATES = { draft: "Draft poll", open: "Voting open", closing: "Review results", closed: "Results accepted", cancelled: "Poll cancelled" };
function element(tag, className, content) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (content !== undefined) el.textContent = content;
  return el;
}

/** drafts retains local form state across repeated session updates. */
export function pollElement(snapshot, poll, hooks, drafts) {
  const d = poll.data, model = pollModel(snapshot, poll);
  const automatic = snapshot.session?.automatic_workspace;
  const mine = snapshot.members?.find(m => m.id === snapshot.actor_id);
  const canEdit = snapshot.session?.state === "active" && ["facilitator", "participant"].includes(mine?.role);
  const el = element("article", `note wide item poll ${d.state === "closed" ? "item-accepted" : "item-provisional"}`);
  el.dataset.id = poll.id; el.dataset.kind = "poll";
  el.dataset.revision = String(poll.position?.revision ?? 0);
  el.setAttribute("aria-label", d.question || "New voting poll");
  const badge = element("span", "badge status");
  badge.append(element("span", "dot"), document.createTextNode(automatic ? "AI organised" : d.state === "closed" ? "Accepted" : "Provisional"));
  el.append(badge, element("span", "kind", automatic && d.state === "closed" ? "Voting finished" : STATES[d.state]),
    element("h2", "text t-body strong", d.question || "What are we voting on?"), element("p", "t-meta poll-prompt", d.prompt));
  if (automatic && d.state !== "draft") el.querySelector(".poll-prompt").remove();
  if (model.pending.length) el.append(element("p", "t-meta", `${model.pending.length} replies processing…`));
  const state = drafts.get(poll.id) ?? {};
  drafts.set(poll.id, state);
  const send = (operation, extra = {}) => hooks.send(operation, { poll_id: poll.id, expected_revision: poll.revision, ...extra });
  function button(label, action, enabled = true, key = label) {
    const b = element("button", "btn btn-secondary btn-sm", label);
    b.type = "button"; b.disabled = !canEdit || !enabled;
    b.dataset.focusKey = `poll-${poll.id}-${key}`;
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await action(); } catch { /* Shared send reports the error. */ }
      finally { if (b.isConnected) b.disabled = !canEdit || !enabled; }
    });
    return b;
  }
  function field(label, control, key = label) {
    const wrap = element("label", "poll-field t-meta");
    wrap.append(document.createTextNode(label), control);
    control.dataset.focusKey = `poll-${poll.id}-${key}`; control.disabled = !canEdit;
    return wrap;
  }
  function select(items, key, label) {
    const input = element("select"); input.setAttribute("aria-label", label);
    input.append(element("option", "", "Choose…")); input.firstChild.value = "";
    for (const [value, name] of items) {
      const option = element("option", "", name); option.value = value; input.append(option);
    }
    input.value = state[key] || "";
    input.addEventListener("change", () => { state[key] = input.value; });
    return input;
  }
  function details(key, label, className) {
    const wrap = element("details", className); wrap.open = state[key] || false;
    wrap.addEventListener("toggle", () => { state[key] = wrap.open; });
    wrap.append(element("summary", "t-meta", label)); return wrap;
  }
  if (d.state === "draft") {
    if (state.definitionRevision !== poll.revision && !state.dirty) {
      state.question = d.question; state.options = d.options.map(o => o.label).join("\n"); state.definitionRevision = poll.revision;
    }
    const q = element("textarea"); q.rows = 2; q.maxLength = 500; q.value = state.question ?? d.question;
    const choices = element("textarea"); choices.rows = 3; choices.value = state.options ?? "";
    q.addEventListener("input", () => { state.question = q.value; state.dirty = true; });
    choices.addEventListener("input", () => { state.options = choices.value; state.dirty = true; });
    const form = element("div", "poll-form");
    form.append(field("Question", q), field("Choices, one per line", choices));
    form.append(button("Save draft", async () => {
      await send("poll.edit", { question: q.value, options: choices.value.split("\n").map(v => v.trim()).filter(Boolean) }); state.dirty = false;
    }), button("Start voting", async () => {
      if (state.dirty) { hooks.attention("Save the changed draft before starting voting."); return; }
      await send("poll.confirm");
    }, Boolean(d.question && d.options.length >= 2)));
    el.append(form);
    if (!snapshot.session?.poll_ai?.available) el.append(element("p", "t-meta", snapshot.session?.poll_ai?.notice || "Voice AI is unavailable. Fill the draft manually."));
  } else if (d.options.length) {
    const tally = pollTally(model);
    const list = element("ol", "poll-options");
    list.dataset.outcome = tally.outcome;
    for (const o of tally.rows) {
      const row = element("li", "poll-option"), line = element("div", "poll-option-heading");
      row.dataset.optionId = o.id;
      line.append(element("span", "t-body", `${o.letter} · ${o.label}`));
      const mark = tallyMark(o.mark, d.state);
      if (mark) { row.dataset.mark = o.mark; line.append(element("span", "poll-mark", mark)); }
      // The bar is drawn, and its words are on it: the count and who chose it.
      const bar = element("div", "poll-bar");
      bar.style.setProperty("--share", String(o.share));
      bar.setAttribute("role", "img");
      bar.setAttribute("aria-label", `${o.label}: ${o.count} of ${model.voted} votes${o.names.length ? `, ${o.names.join(", ")}` : ""}${mark ? `, ${mark.toLowerCase()}` : ""}`);
      const fill = element("span", "poll-bar-fill"); fill.setAttribute("aria-hidden", "true");
      const words = element("span", "poll-bar-words"); words.setAttribute("aria-hidden", "true");
      words.append(element("span", "t-signal poll-count", String(o.count)), element("span", "poll-voters", o.names.join(", ") || "No votes"));
      bar.append(fill, words);
      row.append(line, bar);
      list.append(row);
    }
    el.append(list, element("p", "t-meta poll-turnout", `${model.voted} voted · ${model.notVoted} not voted`));
    if (d.state !== "closed" && !automatic) el.append(element("p", "t-meta", "Voice-inferred votes remain provisional until results are accepted."));
    if (d.state === "open" || automatic && d.state === "closed") {
      const manual = details("manualOpen", "Record or correct a choice", "poll-manual");
      const who = select(model.profiles.map(p => [p.id, p.data.name]), "speaker", "Speaker for manual choice");
      const choice = select([...d.options.map(o => [o.id, o.label]), ["remove", "Withdraw vote"]], "choice", "Manual choice");
      manual.append(field("Speaker", who), field("Choice", choice), button("Record choice", () => {
        if (!who.value || !choice.value) { hooks.attention("Choose both the speaker and their choice."); return; }
        return send("poll.vote", { speaker_profile_id: who.value, option_id: choice.value === "remove" ? null : choice.value });
      }), element("p", "t-meta", model.profiles.length ? "Manual changes record you as the operator acting for the selected speaker." : "Enrol speakers in the Speakers panel first."));
      el.append(manual);
    }
  }
  for (const w of model.unresolved) {
    const wd = w.data, source = snapshot.records.find(r => r.id === wd.source_id);
    const review = details(`review-${w.id}`, wd.status === "clarify" ? "Reply needs clarification" : "Interpretation needs review", "poll-clarification");
    review.append(element("p", "t-body", source?.data.text || "Source unavailable"), element("p", "t-meta", wd.error || wd.prompt));
    if (["open", "closing"].includes(d.state) || automatic && d.state === "closed") {
      const speaker = select(model.profiles.map(p => [p.id, p.data.name]), `who-${w.id}`, "Speaker for unclear reply");
      const choice = select([...d.options.map(o => [o.id, o.label]), ["remove", "Withdraw vote"]], `choice-${w.id}`, "Choice for unclear reply");
      review.append(field("Speaker", speaker, `who-${w.id}`), field("Choice", choice, `choice-${w.id}`), button("Apply correction", () => {
        if (!speaker.value || !choice.value) { hooks.attention("Choose a speaker and option, or exclude the reply."); return; }
        return send("poll.resolve", { work_id: w.id, dismiss: false, speaker_profile_id: speaker.value, option_id: choice.value === "remove" ? null : choice.value });
      }, true, `resolve-${w.id}`));
    }
    review.append(button("Exclude reply", () => send("poll.resolve", { work_id: w.id, dismiss: true }), true, `exclude-${w.id}`));
    if (["error", "uncertain"].includes(wd.status) && wd.epoch === d.epoch && snapshot.session?.poll_ai?.available) {
      const ack = element("input"); ack.type = "checkbox";
      review.append(field("A retry may incur additional API cost", ack, `ack-${w.id}`), button("Retry interpretation", () => {
        if (!ack.checked) { hooks.attention("Acknowledge possible extra API cost before retrying."); return; }
        return send("poll.retry", { work_id: w.id, acknowledge_unknown_cost: true });
      }, true, `retry-${w.id}`));
    }
    el.append(review);
  }
  const evidence = details("evidenceOpen", "Question and vote evidence", "poll-evidence");
  for (const id of d.source_ids ?? []) {
    const source = snapshot.records.find(r => r.id === id);
    if (source) evidence.append(element("p", "t-meta", `Question source: ${source.data.text}`));
  }
  for (const b of model.ballots) {
    const bd = b.data, profile = model.profiles.find(p => p.id === bd.speaker_profile_id);
    const choice = d.options.find(o => o.id === bd.option_id)?.label ?? "Withdrawn";
    const source = snapshot.records.find(r => r.id === bd.source_id);
    evidence.append(element("p", "t-meta", `${profile?.data.name ?? "Unknown speaker"}: ${choice}. ${bd.origin === "human" ? "Manually recorded" : "Voice inferred"}. ${source?.data.text ?? "Recorded using canvas controls"}`));
  }
  el.append(evidence);
  const controls = element("div", "note-actions");
  if (d.state === "open") controls.append(button("Close voting", () => send("poll.close")));
  if (d.state === "closing" && !automatic) controls.append(button("Accept results", () => send("poll.finalise"), !model.pending.length && !model.unresolved.length));
  if (["draft", "open", "closing"].includes(d.state)) controls.append(button("Cancel poll", () => send("poll.cancel")));
  el.append(controls);
  return el;
}
