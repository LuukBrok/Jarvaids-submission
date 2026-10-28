import { CALENDAR_STATES, calendarContent, calendarRows, calendarSummary, taskChangesElement } from "./calendar.mjs";
import { dateChip, dateChipElement } from "./chips.mjs";
/** Source-backed command documents. To-do lists and requirements share collection controls. */
const STATES = { collecting: "Collecting tasks", reviewing: "Review tasks", accepted: "Accepted list", cancelled: "Cancelled list" };
const PENDING = new Set(["queued", "running"]);
const UNRESOLVED = new Set(["clarify", "error", "uncertain", "stale"]);
function element(tag, cls = "", value = "") {
  const el = document.createElement(tag); el.className = cls; el.textContent = value; return el;
}
export function documentModel(snapshot, record) {
  const ids = new Set(record.data.entry_ids);
  const entries = snapshot.records.filter(r => r.kind === "command_entry" && ids.has(r.id) && !r.data.removed);
  const work = snapshot.records.filter(r => r.kind === "command_work" && r.data.document_id === record.id);
  const interpreted = new Set(work.filter(w => ["done", "clarify", "resolved"].includes(w.data.status)).flatMap(w => w.data.sources.map(s => s.id)));
  const covered = new Set(work.flatMap(w => w.data.sources.map(s => s.id)));
  return { entries, work, pending: work.filter(w => PENDING.has(w.data.status)),
    unresolved: work.filter(w => UNRESOLVED.has(w.data.status)), processed: interpreted.size,
    total: covered.size + record.data.uncovered,
    incomplete: Boolean(record.data.uncovered || work.some(w => w.data.status === "dismissed")) };
}

/** A task row's chips: who owns it and when it is due. The date is the
 * resolved deadline_date in the session's zone (chips.mjs); a spoken deadline
 * that has no exact date yet is shown as said, in quotes, never guessed. In
 * the legacy review mode an empty owner or date is named, as before. */
export function taskChips(entry, zone, automatic, now = new Date()) {
  const d = entry.data, row = element("div", "document-task-chips");
  if (d.owner || !automatic) {
    const owner = element("span", "owner-chip", d.owner || "Unassigned");
    owner.setAttribute("aria-label", `Owner: ${d.owner || "Unassigned"}`); row.append(owner);
  }
  const chip = dateChip({ date: d.deadline_date, done: d.done }, zone, now);
  if (chip) row.append(dateChipElement({ ...chip, title: `Deadline ${chip.title}` }));
  else if (d.deadline || !automatic) {
    const said = dateChipElement({ tone: "plain", text: d.deadline ? `“${d.deadline}”` : "No deadline",
      title: d.deadline ? `Deadline as said: ${d.deadline}. No exact date yet` : "No deadline" });
    said.classList.add("date-chip-said"); row.append(said);
  }
  return row.children.length ? row : null;
}

/** Who may edit a document, its drafts, and the `send` and `button` every
 * control on it uses. Exported so the Calendar view (calendar-view.mjs)
 * sends exactly what the card and the list send, with the same refusals. */
export function documentControls(snapshot, record, hooks, drafts = new Map()) {
  const d = record.data;
  const member = snapshot.members?.find(m => m.id === snapshot.actor_id);
  const canEdit = ["facilitator", "participant"].includes(member?.role) && snapshot.session?.state === "active";
  const editable = canEdit && ["collecting", "reviewing"].includes(d.state);
  const state = drafts.get(record.id) ?? {}; drafts.set(record.id, state);
  const send = (operation, extra = {}) => hooks.send(operation, { document_id: record.id, expected_revision: record.revision, ...extra });
  function button(label, action, enabled = true, key = label) {
    const b = element("button", "btn btn-secondary btn-sm", label); b.type = "button";
    b.disabled = !canEdit || !enabled; b.dataset.focusKey = `doc-${record.id}-${key}`;
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { await action(); } catch { /* Shared command handler reports errors. */ }
      finally { if (b.isConnected) b.disabled = !canEdit || !enabled; }
    }); return b;
  }
  return { canEdit, editable, state, send, button };
}

/** A command document as a card. A calendar on the canvas is a compact
 * summary with "Open calendar", because its grid needs the Calendar view's
 * room; the list passes `{ fullCalendar: true }` and keeps the whole
 * calendar in words. To-do lists and requirements are unchanged. */
export function documentElement(snapshot, record, hooks, drafts = new Map(), { fullCalendar = false } = {}) {
  const d = record.data, model = documentModel(snapshot, record);
  const automatic = snapshot.session?.automatic_workspace;
  const criteria = d.document_type === "requirements";
  const calendar = d.document_type === "calendar";
  const compact = calendar && !fullCalendar;
  const noun = calendar ? "calendar" : criteria ? "requirements and wishes" : "to-do list";
  const fields = criteria ? ["text", "category", "basis", "conflict"] : ["text", "owner", "deadline", "classification", "done"];
  const categories = [["requirement", "Requirements"], ["wish", "Wishes"], ["clarification", "Needs clarification"]];
  const conflictCount = model.entries.filter(r => r.data.conflict).length;
  const { canEdit, editable, state, send, button } = documentControls(snapshot, record, hooks, drafts);
  const el = element("article", `note wide item poll command-document ${d.state === "accepted" ? "item-accepted" : "item-provisional"}${calendar ? " calendar-document" : ""}`);
  el.dataset.id = record.id; el.dataset.kind = "command_document";
  el.dataset.revision = String(record.position?.revision ?? 0); el.setAttribute("aria-label", d.title);
  function details(key, label, open = false) {
    const box = element("details"); box.open = state[key] ?? open;
    box.append(element("summary", "t-meta", label));
    box.addEventListener("toggle", () => { state[key] = box.open; }); return box;
  }
  const badge = element("span", "badge status");
  badge.append(element("span", "dot"), document.createTextNode(automatic ? "AI organised" : d.state === "accepted" ? "Accepted" : "Provisional"));
  el.append(badge, element("span", "kind", calendar ? CALENDAR_STATES[d.state] : criteria ? ({ collecting: "Collecting criteria", reviewing: "Review criteria", accepted: "Accepted list", cancelled: "Cancelled list" })[d.state] : STATES[d.state]), element("h2", "t-body strong", d.title));
  const calendarCount = rows => {
    const events = rows.filter(r => !r.task).length, tasks = rows.length - events;
    return `${events} ${events === 1 ? "event" : "events"} · ${tasks} linked ${tasks === 1 ? "task" : "tasks"}`;
  };
  el.append(element("p", "t-meta", calendar ? calendarCount(calendarRows(snapshot, record)) : criteria ? `${model.entries.length} criteria · ${conflictCount} conflicts to review`
    : `${model.entries.filter(r => r.data.done).length} of ${model.entries.length} tasks complete`));
  // The compact card: the next three dated entries and the way to the view.
  // Its controls stay in the disclosure below, closed until wanted.
  if (compact) el.append(calendarSummary(snapshot, record, () => el.dispatchEvent(new CustomEvent("jv:open-calendar", { bubbles: true, detail: { documentId: record.id } }))));
  const body = details("expanded", calendar ? "Calendar, evidence and controls" : criteria ? "Criteria, evidence and controls" : "Tasks, evidence and controls", !compact);
  body.append(element("p", "t-meta document-prompt", d.prompt),
    element("p", "t-meta document-coverage", `${model.processed} of ${model.total} transcript segments interpreted`));
  if (d.state === "reviewing") body.append(element("p", "t-meta", "You can continue your discussion and accept this list later. Transcription and other commands keep working."));
  if (model.pending.length) body.append(element("p", "t-meta", `${model.pending.length} batches processing…`));
  if (model.incomplete) body.append(element("p", "t-meta", "Coverage is incomplete. Some transcript is unprocessed or was excluded."));
  if (!snapshot.session?.command_ai?.available && editable)
    body.append(element("p", "t-meta", snapshot.session?.command_ai?.notice || "Document AI is unavailable. Edit the list manually."));
  if (editable) {
    const titleEditor = details("title-editor", "Edit list title");
    const title = element("input"); title.value = state.title ?? d.title;
    title.dataset.focusKey = `doc-${record.id}-title`;
    title.addEventListener("input", () => { state.title = title.value; });
    const label = element("label", "poll-field t-meta"); label.append(document.createTextNode("List title"), title);
    titleEditor.append(label, button("Save title", () => send("document.edit", { title: title.value })));
    body.append(titleEditor);
  }
  if (d.accepted_snapshot && d.state !== "accepted") {
    const prior = details("previous-acceptance", "Previously accepted version");
    for (const entry of d.accepted_snapshot.filter(e => !e.removed))
      prior.append(element("p", "t-meta", calendar ? `${entry.text} · ${entry.date || "Unscheduled"}` : criteria ? `${entry.text} · ${entry.category} · ${entry.basis === "inferred" ? "AI suggestion" : "Stated criterion"}` : `${entry.text} · ${entry.owner || "Unassigned"} · ${entry.deadline || "Unscheduled"} · ${entry.done ? "Complete" : "Incomplete"}`));
    if (calendar) for (const entry of d.linked_snapshot || []) prior.append(element("p", "t-meta", `${entry.text} · ${entry.deadline_date || entry.deadline || "Unscheduled"} · ${entry.done ? "Complete" : "Incomplete"}`));
    body.append(prior);
  }

  // The compact card leaves the calendar's entries to the Calendar view.
  if (calendar) { if (!compact) body.append(calendarContent(snapshot, record, hooks, state, editable, send, button)); }
  else {
  function taskEditor(entry = null) {
    const key = entry?.id ?? "new";
    const initial = entry?.data ?? (criteria ? { text: "", category: "clarification", basis: "stated", conflict: "" } : { text: "", owner: "", deadline: "", classification: "suggested", done: false });
    const saved = state[`task-${key}`];
    const values = saved?.dirty ? saved : { ...initial }; state[`task-${key}`] = values;
    for (const name of fields)
      if (!values.changed?.has(name)) values[name] = initial[name];
    const form = details(`edit-${key}`, criteria ? (entry ? "Edit criterion" : "Add a criterion manually") : (entry ? "Edit task" : "Add a task manually"));
    const labels = criteria ? [["text", "Criterion"], ["category", "Section"], ["basis", "Basis"], ["conflict", "Conflict to review (clear after resolving)"]]
      : [["text", "Task"], ["owner", "Owner"], ["deadline", "Deadline"], ["classification", "Action type"]];
    for (const [name, label] of labels) {
      const choices = name === "classification" ? [["suggested", "Suggested task"], ["agreed", "Agreed action"]]
        : name === "category" ? categories : name === "basis" ? [["stated", "Stated criterion"], ["inferred", "AI suggestion from discussion"]] : null;
      const input = element(choices ? "select" : ["text", "conflict"].includes(name) ? "textarea" : "input");
      if (choices) for (const [value, text] of choices) {
        const option = element("option", "", text); option.value = value; input.append(option);
      }
      input.value = values[name]; input.disabled = !editable; input.setAttribute("aria-label", label);
      input.dataset.focusKey = `doc-${record.id}-${key}-${name}`;
      input.addEventListener("input", () => {
        values[name] = input.value; values.dirty = true;
        values.changed ??= new Set(); values.changed.add(name);
      });
      const field = element("label", "poll-field t-meta"); field.append(document.createTextNode(label), input); form.append(field);
    }
    form.append(button(criteria ? (entry ? "Save criterion" : "Add criterion") : (entry ? "Save task" : "Add task"), async () => {
      const task = Object.fromEntries(fields.map(k =>
        [k, values.changed?.has(k) || !entry ? values[k] : entry.data[k]]));
      delete state[`task-${key}`];
      try { await send("document.entry.edit", { entry_id: entry?.id ?? "", task, removed: false }); }
      catch (error) { state[`task-${key}`] = values; throw error; }
    }, editable, `save-${key}`));
    return form;
  }
  const list = element("div", "document-entries");
  const sections = new Map();
  if (criteria) for (const [key, title] of categories) {
    const section = element("section", "document-section"); section.dataset.category = key;
    const label = element("h3", "t-body strong document-section-label", title);
    const count = element("span", "t-signal document-section-count", ""); count.setAttribute("aria-hidden", "true");
    label.append(count);
    section.append(label);
    const rows = element("ol", "document-tasks"); section.append(rows); sections.set(key, rows); list.append(section);
  }
  const taskRows = criteria ? null : element("ol", "document-tasks"); if (taskRows) list.append(taskRows);
  for (const entry of model.entries) {
    const row = element("li", "document-task"); row.dataset.entryId = entry.id;
    if (criteria) {
      const basis = element("p", "t-meta document-basis", automatic ? (entry.data.basis === "inferred" ? "AI suggestion" : "Stated criterion") : `${entry.data.basis === "inferred" ? "AI suggestion from discussion" : "Stated criterion"} · ${entry.data.status === "accepted" ? "Accepted" : "Provisional"}`);
      basis.dataset.basis = entry.data.basis === "inferred" ? "inferred" : "stated";
      row.append(element("p", "t-body strong document-criterion-text", entry.data.text), basis);
      if (entry.data.conflict) { row.classList.add("document-task-conflict"); row.append(element("p", "t-meta document-conflict", `Potential conflict: ${entry.data.conflict}`)); }
    } else {
    const heading = element("label", "document-task-heading t-body");
    const done = element("input"); done.type = "checkbox"; done.checked = entry.data.done; done.disabled = !editable;
    done.setAttribute("aria-label", `Complete ${entry.data.text}`);
    done.dataset.focusKey = `doc-${record.id}-${entry.id}-done`;
    done.addEventListener("change", async () => {
      done.disabled = true;
      try { await send("document.entry.edit", { entry_id: entry.id,
        task: { text: entry.data.text, owner: entry.data.owner, deadline: entry.data.deadline,
          classification: entry.data.classification, done: done.checked }, removed: false }); }
      catch { if (done.isConnected) { done.checked = entry.data.done; done.disabled = !editable; } }
    });
    heading.append(done, element("span", "document-task-text", entry.data.text));
    row.dataset.done = String(Boolean(entry.data.done));
    row.append(heading);
    const chips = taskChips(entry, snapshot.session?.timezone, automatic);
    if (chips) row.append(chips);
    if (!automatic) row.append(element("p", "t-meta", `${entry.data.classification === "agreed" ? "Agreed action" : "Suggested task"} · ${entry.data.status === "accepted" ? "Accepted" : "Provisional"}`));
    }
    if (editable) {
      row.append(taskEditor(entry), button(criteria ? "Remove criterion" : "Remove task", () => send("document.entry.edit", {
        entry_id: entry.id, task: Object.fromEntries(fields.map(k => [k, entry.data[k]])), removed: true,
      }), true, `remove-${entry.id}`));
    }
    const evidence = details(`evidence-${entry.id}`, criteria ? "Criterion evidence" : "Task evidence");
    if (!criteria && entry.data.deadline) evidence.append(element("p", "t-meta", `Deadline as said: “${entry.data.deadline}”`));
    for (const ref of entry.data.source_refs) {
      const source = snapshot.records.find(r => r.id === ref.id);
      evidence.append(element("p", "t-meta", `${source?.data.speaker_name || "Meeting transcript"}: “${ref.quote}”${source?.revision !== ref.revision ? " (source changed)" : ""}`));
    }
    if (!entry.data.source_refs.length) evidence.append(element("p", "t-meta", "Entered manually."));
    row.append(evidence); (criteria ? sections.get(entry.data.conflict ? "clarification" : entry.data.category) : taskRows).append(row);
  }
  if (criteria) for (const rows of sections.values()) {
    const count = rows.querySelectorAll(":scope > .document-task").length;
    rows.parentElement.querySelector(".document-section-count").textContent = String(count);
    if (!count) rows.append(element("li", "t-meta", "No criteria in this section yet."));
  }
  body.append(list);
  if (!model.entries.length) body.append(element("p", "t-meta", criteria ? "No criteria found yet. Discuss requirements or preferences, or add one manually." : "No tasks found yet. Continue discussing actions or add one manually."));
  if (editable) body.append(taskEditor());
  }
  const proposed = taskChangesElement(snapshot, record, send, button);
  body.append(proposed);
  if (compact) body.append(element("p", "t-meta", d.state === "reviewing" && calendarRows(snapshot, record).some(row => row.task)
    ? "Events, dates and evidence are in the Calendar view. Accepting this calendar also confirms the shared task details shown there."
    : "Events, dates and evidence are in the Calendar view."));
  for (const work of model.unresolved) {
    const review = details(`work-${work.id}`, work.data.status === "clarify" ? "Reply needs clarification" : "Interpretation needs review", true);
    review.append(element("p", "t-meta", work.data.error || work.data.prompt));
    for (const ref of work.data.sources) {
      const source = snapshot.records.find(r => r.id === ref.id);
      if (source) review.append(element("p", "t-meta", source.data.text));
    }
    if (editable) {
      review.append(button("Exclude interpretation", () => send("document.resolve", { work_id: work.id }), true, `exclude-${work.id}`));
      const label = element("label", "poll-field t-meta"), ack = element("input"); ack.type = "checkbox";
      ack.checked = state[`retry-${work.id}`] || false;
      ack.addEventListener("change", () => { state[`retry-${work.id}`] = ack.checked; });
      label.append(ack, document.createTextNode("A retry may incur additional API cost"));
      review.append(label, button("Retry interpretation", () => {
        if (!ack.checked) { hooks.attention("Acknowledge possible additional API cost before retrying."); return; }
        return send("document.retry", { work_id: work.id, acknowledge_unknown_cost: true });
      }, Boolean(snapshot.session?.command_ai?.available), `retry-${work.id}`));
    }
    body.append(review);
  }
  const controls = element("div", "note-actions");
  if (d.state === "collecting") controls.append(button("Refresh collection", () => send("document.refresh")), button(`Close ${noun}`, () => send("document.close")));
  if (d.state === "reviewing" && !automatic) {
    let acknowledgement = null;
    if (model.incomplete) {
      const label = element("label", "poll-field t-meta"); acknowledgement = element("input"); acknowledgement.type = "checkbox";
      acknowledgement.checked = state.coverageAckRevision === record.revision;
      acknowledgement.addEventListener("change", () => { state.coverageAckRevision = acknowledgement.checked ? record.revision : null; });
      label.append(acknowledgement, document.createTextNode("Accept a list with incomplete transcript coverage")); body.append(label);
    }
    controls.append(button(`Accept ${noun}`, () => send("document.accept", { acknowledge_incomplete: acknowledgement?.checked ?? false }),
      !model.pending.length && !model.unresolved.length && !conflictCount && !proposed.children.length));
  }
  if (["accepted", "reviewing"].includes(d.state)) controls.append(button(`Reopen ${noun}`, () => send("document.reopen")));
  if (editable) controls.append(button(`Cancel ${noun}`, () => send("document.cancel")));
  body.append(controls);
  if (automatic) {
    el.querySelector(".kind").textContent = d.state === "collecting" ? "Collecting" : d.state === "cancelled" ? "Cancelled" : "Collection stopped";
    const content = element("div", "command-content");
    const more = details("command-details", "Details and controls"); more.className = "command-details";
    for (const child of [...body.children]) {
      if (child.tagName === "SUMMARY") continue;
      (child.matches(".document-entries, .calendar-content") ? content : more).append(child);
    }
    // The useful text stays visible; editing and evidence remain one click away.
    for (const row of content.querySelectorAll(".document-task")) {
      const rowDetails = details(`row-${row.dataset.entryId}`, "Details");
      for (const child of [...row.children])
        if (child.matches("details, button")) rowDetails.append(child);
      if (rowDetails.children.length > 1) row.append(rowDetails);
    }
    if (criteria) for (const section of content.querySelectorAll(".document-section"))
      if (!section.querySelector(".document-task")) section.hidden = true;
    if (model.pending.length) content.append(element("p", "t-meta", "Updating…"));
    if (model.unresolved.length) content.append(element("p", "t-meta", `${model.unresolved.length} unclear replies in Details`));
    el.append(content, more);
  } else el.append(body);
  return el;
}
