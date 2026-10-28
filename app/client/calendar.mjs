/** Calendar views use date strings, so navigation cannot shift dates across zones.
 * The date helpers, the period arithmetic, the focus rule and the entry
 * builders are exported, because the canvas card, the list and the Calendar
 * view (calendar-view.mjs) must show the same dates and send the same
 * operations; a second copy would drift. */
function el(tag, cls = "", value = "") { const node = document.createElement(tag); node.className = cls; node.textContent = value; return node; }
export const parsed = value => new Date(`${value}T12:00:00Z`);
export const iso = value => value.toISOString().slice(0, 10);
export const format = (value, options) => new Intl.DateTimeFormat("en-GB", { ...options, timeZone: "UTC" }).format(parsed(value));
export function move(value, amount, unit) {
  const d = parsed(value);
  if (unit === "year") { d.setUTCDate(1); d.setUTCFullYear(d.getUTCFullYear() + amount); }
  else if (unit === "month") { d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + amount); }
  else d.setUTCDate(d.getUTCDate() + amount * (unit === "week" ? 7 : 1));
  return iso(d);
}
export function monday(value) { const d = parsed(value); d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7); return iso(d); }
export function startMonth(value) { return value.slice(0, 8) + "01"; }
export const VIEWS = ["day", "week", "month", "year"];
/** A calendar's state in words, on the card and in the Calendar view. */
export const CALENDAR_STATES = { collecting: "Collecting calendar", reviewing: "Review calendar", accepted: "Accepted calendar", cancelled: "Cancelled calendar" };

/** The half-open period [start, end) a view shows around a date. */
export function periodRange(view, date) {
  let start = date, end = move(start, 1, "day");
  if (view === "week") { start = monday(date); end = move(start, 1, "week"); }
  if (view === "month") { start = startMonth(date); end = move(start, 1, "month"); }
  if (view === "year") { start = date.slice(0, 4) + "-01-01"; end = move(start, 1, "year"); }
  return { start, end };
}

/** The period's heading: "2027", "October 2026", "19 Oct – 25 Oct 2026" or a full day. */
export function periodTitle(view, start, end) {
  return view === "year" ? start.slice(0, 4) : view === "month"
    ? format(start, { month: "long", year: "numeric" }) : view === "week" ? `${format(start, { day: "numeric", month: "short" })} – ${format(move(end, -1, "day"), { day: "numeric", month: "short", year: "numeric" })}`
      : format(start, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

/** Today's date in the meeting's time zone, as an ISO date string. */
export function todayIn(timezone, now = new Date()) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now).map(p => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** The shared navigation state of one calendar (kept in the document's
 * drafts, so the list, the card and the Calendar view agree). A new focus
 * from the server is applied unless a person navigated here since; a voice
 * command ("show week view") always wins. Returns the navigation state. */
export function calendarNav(state, d) {
  state.calendar ??= {};
  const nav = state.calendar;
  if (nav.focusRevision !== d.calendar_focus_revision) {
    if (!nav.touched || d.calendar_focus_origin === "voice")
      Object.assign(nav, { view: d.calendar_view || "month", date: d.calendar_date, touched: false });
    nav.focusRevision = d.calendar_focus_revision;
  }
  return nav;
}

export function calendarRows(snapshot, doc) {
  const events = new Set(doc.data.entry_ids), tasks = new Set(doc.data.task_ids || []);
  return snapshot.records.filter(r => r.kind === "command_entry" && !r.data.removed && (events.has(r.id) || tasks.has(r.id)))
    .map(r => ({ record: r, id: r.id, task: tasks.has(r.id), text: r.data.text,
      date: tasks.has(r.id) ? r.data.deadline_date || "" : r.data.date || "",
      phrase: tasks.has(r.id) ? r.data.deadline || "" : r.data.date_phrase || "",
      time: tasks.has(r.id) ? "" : r.data.time || "", done: r.data.done,
      clarification: tasks.has(r.id) ? r.data.deadline_clarification || "" : r.data.clarification || "" }));
}

/** "From a note" on an event made from a note's details (board.mjs), with
 * the note's words, so the calendar says where a manual event came from.
 * Kept apart from calendarContent so a rewrite of the view merges cleanly. */
export function noteSourceLine(snapshot, record) {
  const id = record?.data?.note_id;
  if (!id) return null;
  const note = snapshot.records.find(r => r.id === id && r.kind === "item" && r.data.status === "accepted");
  const short = note && (note.data.text.length > 80 ? `${note.data.text.slice(0, 79)}…` : note.data.text);
  const line = el("p", "t-meta calendar-from-note", note ? `From a note: “${short}”` : "From a note that is no longer on the canvas");
  line.dataset.noteId = id;
  return line;
}

export function taskChangesElement(snapshot, doc, send, button) {
  const ids = new Set(doc.data.document_type === "calendar" ? doc.data.task_ids : doc.data.entry_ids);
  const host = el("div", "task-changes");
  for (const change of snapshot.records.filter(r => r.kind === "command_task_change" && ids.has(r.data.task_id) && r.data.state === "pending")) {
    const task = snapshot.records.find(r => r.id === change.data.task_id), value = change.data.values;
    const row = el("section", "document-task"); row.dataset.changeId = change.id;
    row.append(el("h3", "t-body strong", "Proposed task update"),
      el("p", "t-meta", `Current: ${task?.data.text || "Task unavailable"} · ${task?.data.deadline_date || task?.data.deadline || "Unscheduled"} · ${task?.data.done ? "Complete" : "Incomplete"} · Owner: ${task?.data.owner || "Unassigned"} · ${task?.data.classification || "suggested"}`),
      el("p", "t-body", `Proposed: ${value.text} · ${value.deadline_date || value.deadline || "Unscheduled"} · ${value.done ? "Complete" : "Incomplete"} · Owner: ${value.owner || "Unassigned"} · ${value.classification} · Spoken date: ${value.deadline || "None"}${value.removed ? " · Remove task" : ""}`));
    const stale = !task || task.revision !== change.data.base_revision;
    if (stale) row.append(el("p", "t-meta", "The task changed since this proposal. Dismiss it and request a fresh interpretation."));
    const evidence = el("details"); evidence.append(el("summary", "t-meta", "Change evidence"));
    for (const ref of change.data.source_refs) evidence.append(el("p", "t-meta", ref.quote));
    row.append(evidence,
      button("Accept task change", () => send("calendar.task.resolve", { change_id: change.id,
        expected_change_revision: change.revision, accept: true }), !stale, `accept-change-${change.id}`),
      button("Dismiss task change", () => send("calendar.task.resolve", { change_id: change.id,
        expected_change_revision: change.revision, accept: false }), true, `dismiss-change-${change.id}`));
    host.append(row);
  }
  return host;
}

/** The entry builders, shared by the list's calendar and the Calendar view:
 * `item(row)` is one entry with its date line, evidence and editor, and
 * `editor(row)` edits a row, or adds an event when `row` is null. Both send
 * `calendar.entry.edit` through the document's own `send` and `button`
 * (documents.mjs documentControls). */
export function entryTools(snapshot, doc, state, editable, send, button) {
  const automatic = snapshot.session?.automatic_workspace;
  function editor(row = null) {
    const key = row?.id || "new-event", saved = state[`calendar-${key}`];
    const initial = { text: row?.text || "", date: row?.date || "", time: row?.time || "", done: row?.done || false };
    const values = saved || { ...initial, changed: new Set() }; state[`calendar-${key}`] = values;
    for (const key of Object.keys(initial)) if (!values.changed.has(key)) values[key] = initial[key];
    const box = el("details"); box.open = state[`calendar-edit-${key}`] || false;
    box.append(el("summary", "t-meta", row ? row.task ? "Edit linked task" : "Edit event" : "Add an event manually"));
    box.addEventListener("toggle", () => { state[`calendar-edit-${key}`] = box.open; });
    for (const [name, label] of [["text", row?.task ? "Task" : "Event"], ["date", "Date"], ["time", "Time"], ["done", "Complete"]]) {
      if (row?.task && name === "time") continue;
      const control = el("input"); control.type = name === "done" ? "checkbox" : name === "date" ? "date" : name === "time" ? "time" : "text";
      if (name === "done") control.checked = values.done; else control.value = values[name];
      control.setAttribute("aria-label", label); control.dataset.focusKey = `doc-${doc.id}-${key}-${name}`;
      control.addEventListener("input", () => { values[name] = name === "done" ? control.checked : control.value; values.changed.add(name); });
      const field = el("label", "poll-field t-meta"); field.append(document.createTextNode(label), control); box.append(field);
    }
    box.append(button(row ? "Save calendar entry" : "Add event", async () => {
      const value = Object.fromEntries(Object.keys(initial).map(k => [k, values.changed.has(k) ? values[k] : initial[k]]));
      value.date_changed = values.changed.has("date") || !row;
      delete state[`calendar-${key}`];
      try { await send("calendar.entry.edit", { entry_id: row && !row.task ? row.id : "", task_id: row?.task ? row.id : "",
        ...(row ? row.task ? { expected_task_revision: row.record.revision } : { expected_entry_revision: row.record.revision } : {}), value, removed: false }); }
      catch (error) { state[`calendar-${key}`] = values; throw error; }
    }, editable, `save-calendar-${key}`));
    if (row) box.append(button(row.task ? "Remove task from both views" : "Remove event", () => send("calendar.entry.edit", {
      entry_id: row.task ? "" : row.id, task_id: row.task ? row.id : "",
      ...(row.task ? { expected_task_revision: row.record.revision } : { expected_entry_revision: row.record.revision }),
      value: { ...initial, date_changed: false }, removed: true,
    }), editable, `remove-calendar-${key}`));
    return box;
  }
  function item(row) {
    const box = el("article", "calendar-entry document-task"); box.dataset.entryId = row.id;
    box.append(el("p", `t-body strong${row.done ? " calendar-complete" : ""}`, row.text),
      el("p", "t-meta", automatic ? `${row.date || "Unscheduled"}${row.time ? " · " + row.time : ""}${row.task && row.record.data.owner ? " · " + row.record.data.owner : ""}` : `${row.task ? "Linked task deadline" : "Event"} · ${row.date || "Unscheduled"}${row.time ? " at " + row.time : ""} · ${row.record.data.status === "accepted" ? "Accepted" : "Provisional"}${row.done ? " · Complete" : ""}`));
    if (row.task && !automatic) box.append(el("p", "t-meta", `Owner: ${row.record.data.owner || "Unassigned"} · ${row.record.data.classification === "agreed" ? "Agreed action" : "Suggested task"}`));
    if (row.phrase && !automatic) box.append(el("p", "t-meta", `${row.record.data.origin === "human" ? "Entered date" : "Spoken date"}: “${row.phrase}”${row.date ? " → " + row.date : ""}`));
    if (row.clarification) box.append(el("p", "t-meta calendar-question", row.clarification));
    const fromNote = noteSourceLine(snapshot, row.record); if (fromNote) box.append(fromNote);
    const evidence = el("details"); evidence.append(el("summary", "t-meta", "Calendar evidence"));
    if (automatic && row.phrase) evidence.append(el("p", "t-meta", `Original date: ${row.phrase}`));
    for (const ref of row.record.data.source_refs || []) evidence.append(el("p", "t-meta", ref.quote));
    if (!row.record.data.source_refs?.length) evidence.append(el("p", "t-meta", "Entered manually."));
    box.append(evidence); if (editable) box.append(editor(row)); return box;
  }
  return { editor, item };
}

/** The calendar's controls: the time zone line, the four view buttons and
 * Previous, Today, Next and the date field. Navigation is local to this
 * screen: `jump(view, date)` moves it and never writes to the record. */
export function calendarToolbar(doc, nav, jump, automatic) {
  const d = doc.data;
  // Focus keys let a redraw put the focus back on the control that moved it.
  const localButton = (label, action) => { const b = el("button", "btn btn-secondary btn-sm", label); b.type = "button"; b.dataset.focusKey = `calendar-${doc.id}-${label}`; b.addEventListener("click", action); return b; };
  const zone = el("p", "t-meta calendar-zone", automatic ? d.timezone : `Meeting time zone: ${d.timezone}. Dates use the recorded speech time.`);
  const views = el("div", "calendar-tools");
  for (const view of VIEWS) {
    const b = localButton(view[0].toUpperCase() + view.slice(1), () => jump(view, nav.date));
    b.setAttribute("aria-pressed", String(view === nav.view)); views.append(b);
  }
  const navigation = el("div", "calendar-tools");
  navigation.append(localButton("Previous", () => jump(nav.view, move(nav.date, -1, nav.view))),
    localButton("Today", () => jump(nav.view, todayIn(d.timezone))),
    localButton("Next", () => jump(nav.view, move(nav.date, 1, nav.view))));
  const dateField = el("input"); dateField.type = "date"; dateField.value = nav.date; dateField.setAttribute("aria-label", "Go to date");
  dateField.dataset.focusKey = `calendar-${doc.id}-date`;
  dateField.addEventListener("change", () => { if (dateField.value) jump(nav.view, dateField.value); }); navigation.append(dateField);
  return { zone, views, navigation, localButton };
}

export function calendarContent(snapshot, doc, hooks, state, editable, send, button) {
  const d = doc.data, rows = calendarRows(snapshot, doc), host = el("div", "calendar-content");
  const automatic = snapshot.session?.automatic_workspace;
  const nav = calendarNav(state, d);
  const jump = (view, date) => { nav.view = view; nav.date = date; nav.touched = true; draw(); };
  const { editor, item } = entryTools(snapshot, doc, state, editable, send, button);
  function draw() {
    host.replaceChildren();
    const { zone, views, navigation, localButton } = calendarToolbar(doc, nav, jump, automatic);
    host.append(zone, views, navigation);
    const count = date => rows.filter(row => row.date === date).length;
    const { start, end } = periodRange(nav.view, nav.date);
    host.append(el("h3", "t-body strong calendar-period", periodTitle(nav.view, start, end)));
    if (nav.view === "year") {
      const year = el("div", "calendar-year");
      for (let i = 0; i < 12; i++) {
        const month = move(start, i, "month"), next = move(month, 1, "month");
        const number = rows.filter(row => row.date >= month && row.date < next).length;
        year.append(localButton(`${format(month, { month: "long" })} · ${number}`, () => jump("month", month)));
      } host.append(year);
    } else if (nav.view !== "day") {
      const grid = el("div", "calendar-grid"); grid.setAttribute("aria-label", `${nav.view} dates`);
      for (const name of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) grid.append(el("span", "t-caption", name));
      const first = nav.view === "month" ? monday(start) : start;
      for (let i = 0; i < (nav.view === "month" ? 42 : 7); i++) {
        const day = move(first, i, "day"), n = count(day);
        const b = localButton(`${Number(day.slice(-2))}${n ? " · " + n : ""}`, () => jump("day", day));
        b.classList.add("calendar-day"); b.dataset.date = day; if (day === nav.date) b.setAttribute("aria-current", "date"); b.setAttribute("aria-label", `${day}, ${n} entries`);
        if (day < start || day >= end) b.classList.add("calendar-outside"); grid.append(b);
      } host.append(grid);
    }
    const scheduled = rows.filter(row => row.date && row.date >= start && row.date < end).sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time));
    const agenda = el("section", "calendar-agenda"); agenda.append(el("h3", "t-body strong", "In this period"));
    for (const row of scheduled) agenda.append(item(row));
    if (!scheduled.length) agenda.append(el("p", "t-meta", "No scheduled entries in this period.")); host.append(agenda);
    const unscheduled = el("section", "calendar-unscheduled"); unscheduled.append(el("h3", "t-body strong", "Unscheduled"));
    for (const row of rows.filter(row => !row.date)) unscheduled.append(item(row));
    if (!rows.some(row => !row.date)) {
      unscheduled.append(el("p", "t-meta", "No undated entries."));
      if (automatic) unscheduled.hidden = true;
    }
    host.append(unscheduled);
    if (editable) host.append(editor());
    if (d.state === "reviewing" && rows.some(row => row.task)) host.append(el("p", "t-meta", "Accepting this calendar also confirms the displayed shared task details. Later AI task changes require review."));
  }
  draw(); return host;
}

/** Entries in reading order: by date, then time (an entry without a time,
 * such as a task deadline, comes first on its day), then words. */
export const byWhen = (a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time) || a.text.localeCompare(b.text);

/** The next `count` dated entries from `today` on. */
export function upcoming(rows, today, count = 3) {
  return rows.filter(row => row.date && row.date >= today).sort(byWhen).slice(0, count);
}

/** What a pill shows and how it is marked. `kind` picks the accent (an event
 * or a linked task); `machine` is true for an entry the interpreter made from
 * speech that no person has accepted, which draws the machine mark, so a
 * model's guess never looks like a person's entry. */
export function pillModel(row) {
  const data = row.record?.data ?? {};
  const kind = row.task ? "task" : "event";
  const owner = row.task ? data.owner || "" : "";
  const machine = data.origin !== "human" && data.status !== "accepted";
  const words = [row.time, row.text, owner && `owner ${owner}`, row.done && "complete",
    machine && "interpreted from the discussion, not accepted"].filter(Boolean);
  return { id: row.id, kind, text: row.text, time: row.time, owner, done: Boolean(row.done), machine,
    label: `${kind === "task" ? "Linked task" : "Event"}: ${words.join(", ")}` };
}

/** One entry as a pill: time in mono, the words, and a task's owner. A
 * button when `onOpen` is given, so a pill in the view opens its details. */
export function pillElement(row, onOpen = null) {
  const p = pillModel(row);
  const pill = el(onOpen ? "button" : "span", `cal-pill cal-pill-${p.kind}${p.machine ? " cal-pill-machine" : ""}${p.done ? " calendar-complete" : ""}`);
  if (onOpen) { pill.type = "button"; pill.dataset.focusKey = `calendar-pill-${row.id}`; pill.addEventListener("click", () => onOpen(row)); }
  pill.dataset.entryId = row.id; pill.dataset.kind = p.kind; pill.setAttribute("aria-label", p.label); pill.title = p.label;
  if (p.time) pill.append(el("span", "cal-pill-time", p.time));
  pill.append(el("span", "cal-pill-text", p.text));
  if (p.owner) pill.append(el("span", "cal-pill-owner", p.owner));
  return pill;
}

/** The canvas card's summary: how many entries, the next three dated ones as
 * pills, how many are unscheduled, and Open calendar. */
export function calendarSummary(snapshot, doc, open) {
  const rows = calendarRows(snapshot, doc), today = todayIn(doc.data.timezone);
  const host = el("div", "calendar-summary");
  const next = upcoming(rows, today);
  host.append(el("p", "t-meta", next.length ? "Next" : rows.some(row => row.date) ? "Nothing dated from today on." : "Nothing dated yet."));
  if (next.length) {
    const list = el("ol", "calendar-summary-list");
    for (const row of next) {
      const item = el("li", "calendar-summary-entry");
      item.append(el("span", "t-signal calendar-summary-date", format(row.date, { weekday: "short", day: "numeric", month: "short" })), pillElement(row));
      list.append(item);
    }
    host.append(list);
  }
  const undated = rows.filter(row => !row.date).length;
  if (undated) host.append(el("p", "t-meta", `${undated} unscheduled`));
  const b = el("button", "btn btn-secondary btn-sm calendar-open", "Open calendar"); b.type = "button";
  b.addEventListener("click", open); host.append(b);
  return host;
}
