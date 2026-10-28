/**
 * The Calendar view: the third view beside Canvas and List (the dock's view
 * toggle, `data-view="calendar"`). It fills the workspace area the canvas
 * uses, with the rail beside it, and draws the session's calendar document
 * as a calendar: month and week as a grid of day cells holding the entries
 * as pills, day as a list by time, year as twelve month cards with counts,
 * and an Unscheduled column at the side.
 *
 * Nothing here is a second calendar. The rows, the dates, the navigation
 * rule, the entry editor and evidence, the task-change review and the
 * operations they send all come from calendar.mjs and documents.mjs, which
 * the list and the canvas card use too, so the three can never disagree.
 * Navigation is shared with the list through the document's drafts.
 *
 * A voice view command ("Hey Jarvaids, show week view") changes the
 * document's focus on the server (calendar.view). The shared rule in
 * calendarNav applies it here as it does in the list, and a new voice focus
 * also brings this view forward, because the room asked to see the calendar.
 *
 * The top half of this file is pure (no DOM at import), so the grid and pill
 * logic is tested without a browser (tests/calendar-view-unit.mjs).
 */
import { CALENDAR_STATES, byWhen, calendarNav, calendarRows, calendarToolbar, entryTools, format, monday, move,
  periodRange, periodTitle, pillElement, taskChangesElement, todayIn } from "./calendar.mjs";
import { documentControls, documentModel } from "./documents.mjs";

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
/** The typed, addressed command the empty state sends: the same words the
 * voice path recognises, through the same route as a typed note. */
export const MAKE_CALENDAR = "Hey Jarvaids, make a calendar";
/** Pills a month cell shows before "+N more": three fit the cell's height at
 * both scales (--cal-cell-month), more would push the grid off the screen. */
export const MONTH_CELL_PILLS = 3;

// ------------------------------------------------------------------ pure

/** The day cells of a month (six whole weeks from the Monday on or before
 * the 1st, so every month has the same grid) or a week (Monday to Sunday). */
export function gridDays(view, date, today = "") {
  if (view !== "month" && view !== "week") return [];
  const { start, end } = periodRange(view, date);
  const first = view === "month" ? monday(start) : start;
  return Array.from({ length: view === "month" ? 42 : 7 }, (_, i) => {
    const day = move(first, i, "day");
    return { date: day, day: Number(day.slice(-2)), outside: day < start || day >= end, today: day === today, current: day === date };
  });
}

/** Dated rows by day, each day in reading order. */
export function entriesByDay(rows) {
  const days = new Map();
  for (const row of [...rows].filter(r => r.date).sort(byWhen)) days.set(row.date, [...(days.get(row.date) ?? []), row]);
  return days;
}

/** What one month cell shows: the first `limit` pills and how many more. */
export function cellEntries(rows, limit = MONTH_CELL_PILLS) {
  return rows.length > limit ? { shown: rows.slice(0, limit - 1), more: rows.length - (limit - 1) } : { shown: rows, more: 0 };
}

/** A day by time: entries without a time (task deadlines, all-day events)
 * first, then the timed ones in order. */
export function dayAgenda(rows, date) {
  const day = rows.filter(r => r.date === date).sort(byWhen);
  return { allDay: day.filter(r => !r.time), timed: day.filter(r => r.time) };
}

/** The year's twelve months with their counts. */
export function yearMonths(rows, year) {
  return Array.from({ length: 12 }, (_, i) => {
    const month = `${year}-${String(i + 1).padStart(2, "0")}-01`, next = move(month, 1, "month");
    const inside = rows.filter(r => r.date && r.date >= month && r.date < next);
    return { month, name: format(month, { month: "long" }), events: inside.filter(r => !r.task).length,
      tasks: inside.filter(r => r.task).length, total: inside.length };
  });
}

/** The session's calendar documents, oldest first. */
export function calendarDocs(snapshot) {
  return (snapshot?.records ?? []).filter(r => r.kind === "command_document" && r.data.document_type === "calendar");
}

/** The calendar to show: the one a person chose (Open calendar, the picker),
 * else the newest still collecting or in review, else the newest accepted,
 * else the newest. */
export function pickCalendar(docs, chosenId = null) {
  const newest = states => [...docs].reverse().find(d => states.includes(d.data.state));
  return docs.find(d => d.id === chosenId) ?? newest(["collecting", "reviewing"]) ?? newest(["accepted"]) ?? docs.at(-1) ?? null;
}

/** The empty state, honestly. A typed command runs only in automatic
 * workspace (API.md, `source.text`), so the button is offered only there;
 * with the command interpreter off nothing could fill a calendar, so it
 * says that instead of offering anything. */
export function emptyState(session) {
  const ai = session?.command_ai;
  if (!ai?.available || (ai.types && !ai.types.includes("calendar"))) {
    return { kind: "off", text: `No calendar in this session yet. The command interpreter is off, so Jarvaids cannot make or fill one from the discussion.${ai?.notice ? " " + ai.notice : ""}` };
  }
  if (session?.automatic_workspace) {
    return { kind: "button", text: "No calendar in this session yet. Jarvaids can make one, then dates said in the meeting land on it." };
  }
  return { kind: "spoken", text: `No calendar in this session yet. Say “${MAKE_CALENDAR}” to start one; typed commands run only in automatic workspace.` };
}

/** True when the server has a newer focus for a calendar from a voice
 * command than this screen last saw. The first sight of a calendar only
 * records its focus, so opening a session or a calendar made "for next week"
 * does not pull the screen away from the canvas. */
export function voiceFocus(seen, doc) {
  const revision = doc.data.calendar_focus_revision ?? 0, before = seen.get(doc.id);
  seen.set(doc.id, revision);
  return before !== undefined && revision > before && doc.data.calendar_focus_origin === "voice";
}

// ------------------------------------------------------------------ the view

function el(tag, cls = "", value = "") { const node = document.createElement(tag); node.className = cls; node.textContent = value; return node; }

export function register(registerTool) {
  const seen = new Map();
  let host = null, chosenId = null, selected = null, signature = "", ctxRef = null;

  /** Rebuilt only when something it shows changed, so an open disclosure, a
   * field being typed into and the focus survive the poll every second. */
  function draw(ctx, snapshot, force = false) {
    const docs = calendarDocs(snapshot);
    const doc = pickCalendar(docs, chosenId);
    const session = snapshot.session;
    const member = snapshot.members?.find(m => m.id === snapshot.actor_id);
    if (!doc) {
      const empty = emptyState(session);
      const active = session?.state === "active" && ["facilitator", "participant"].includes(member?.role);
      const key = JSON.stringify(["empty", empty, active]);
      if (!force && key === signature) return;
      signature = key;
      const box = el("section", "cal-empty");
      box.setAttribute("aria-labelledby", "cal-empty-title");
      const title = el("h2", "t-title", "Calendar"); title.id = "cal-empty-title";
      box.append(title, el("p", "t-body cal-empty-text", empty.text));
      if (empty.kind === "button") {
        const make = el("button", "btn btn-secondary btn-lg", "Make a calendar"); make.type = "button"; make.id = "make-calendar";
        make.disabled = !active;
        make.addEventListener("click", async () => {
          make.disabled = true;
          try { await ctx.send("source.text", { text: MAKE_CALENDAR }); }
          catch { /* send's banner says why; nothing was made */ }
          finally { if (make.isConnected) make.disabled = !active; }
        });
        box.append(make);
        if (!active) box.append(el("p", "t-meta", "Commands can be typed while capture runs."));
      }
      host.replaceChildren(box);
      return;
    }

    const d = doc.data, automatic = session?.automatic_workspace;
    const controls = documentControls(snapshot, doc, { send: ctx.send, attention: ctx.attention }, ctx.board.documentDrafts);
    const nav = calendarNav(controls.state, d);
    const rows = calendarRows(snapshot, doc);
    if (selected && !rows.some(r => r.id === selected)) selected = null;
    const model = documentModel(snapshot, doc);
    const changes = snapshot.records.filter(r => r.kind === "command_task_change" && (d.task_ids || []).includes(r.data.task_id));
    const key = JSON.stringify([docs.map(x => [x.id, x.revision]), rows.map(r => [r.id, r.record.revision]),
      changes.map(c => [c.id, c.revision]), model.work.map(w => [w.id, w.revision]), session?.state, session?.timezone,
      controls.editable, nav.view, nav.date, selected]);
    if (!force && key === signature) return;
    signature = key;

    const active = document.activeElement;
    const hadFocus = host.contains(active) && active !== host;
    const focus = hadFocus ? active.dataset.focusKey : null;
    const caret = typeof active?.selectionStart === "number" ? [active.selectionStart, active.selectionEnd] : null;

    const jump = (view, date) => { nav.view = view; nav.date = date; nav.touched = true; draw(ctx, ctx.app.snapshot, true); };
    const open = row => { selected = row.id; draw(ctx, ctx.app.snapshot, true); host.querySelector(".cal-detail")?.focus(); };
    const { editor, item } = entryTools(snapshot, doc, controls.state, controls.editable, controls.send, controls.button);
    const pill = row => pillElement(row, open);
    const today = todayIn(d.timezone);

    // The head: what this calendar is, and a picker when there are several.
    const head = el("header", "cal-head");
    const name = el("div", "cal-name");
    name.append(el("span", "t-small cal-state", automatic ? "AI organised" : CALENDAR_STATES[d.state] ?? d.state), el("h2", "t-title", d.title));
    head.append(name);
    if (docs.length > 1) {
      const label = el("label", "field cal-picker"); label.append(el("span", "", "Calendar"));
      const select = el("select");
      for (const x of [...docs].reverse()) {
        const option = el("option", "", `${x.data.title} · ${CALENDAR_STATES[x.data.state] ?? x.data.state}`); option.value = x.id;
        option.selected = x.id === doc.id; select.append(option);
      }
      select.addEventListener("change", () => { chosenId = select.value; selected = null; draw(ctx, ctx.app.snapshot, true); });
      label.append(select); head.append(label);
    }

    // The toolbar: the same controls as the list's calendar.
    const { zone, views, navigation } = calendarToolbar(doc, nav, jump, automatic);
    const toolbar = el("div", "cal-toolbar");
    toolbar.append(views, navigation, zone);
    const legend = el("p", "t-small cal-legend");
    legend.append(el("span", "cal-key cal-key-event", "Event"), el("span", "cal-key cal-key-task", "Linked task"),
      el("span", "cal-key cal-key-machine", automatic ? "Dashed: AI organised from the discussion" : "Dashed: interpreted from the discussion, not accepted"));

    // The period.
    const { start, end } = periodRange(nav.view, nav.date);
    const main = el("section", "cal-main");
    const period = el("h3", "t-title cal-period calendar-period", periodTitle(nav.view, start, end));
    period.id = "cal-period"; period.tabIndex = -1;
    main.setAttribute("aria-labelledby", "cal-period");
    main.append(period);
    const byDay = entriesByDay(rows);
    if (nav.view === "month" || nav.view === "week") {
      const grid = el("div", `cal-grid cal-grid-${nav.view}`);
      grid.setAttribute("role", "group"); grid.setAttribute("aria-label", `${nav.view === "month" ? "Month" : "Week"} of ${periodTitle(nav.view, start, end)}`);
      for (const name of WEEKDAYS) grid.append(el("span", "t-small cal-weekday", name));
      for (const cell of gridDays(nav.view, nav.date, today)) {
        const entries = byDay.get(cell.date) ?? [];
        const box = el("div", `cal-cell${cell.outside ? " cal-outside" : ""}${cell.today ? " cal-today" : ""}`);
        box.dataset.date = cell.date;
        const long = format(cell.date, { weekday: "long", day: "numeric", month: "long" });
        const number = el("button", "cal-daynum t-signal", nav.view === "week" ? `${format(cell.date, { weekday: "short" })} ${cell.day}` : String(cell.day));
        number.type = "button"; number.dataset.focusKey = `calendar-day-${cell.date}`; number.setAttribute("aria-label", `${long}, ${entries.length} ${entries.length === 1 ? "entry" : "entries"}`);
        if (cell.current) number.setAttribute("aria-current", "date");
        number.addEventListener("click", () => jump("day", cell.date));
        const pills = el("div", "cal-pills");
        const { shown, more } = nav.view === "month" ? cellEntries(entries) : { shown: entries, more: 0 };
        for (const row of shown) pills.append(pill(row));
        if (more) {
          const rest = el("button", "cal-more t-small", `+${more} more`); rest.type = "button"; rest.dataset.focusKey = `calendar-more-${cell.date}`;
          rest.setAttribute("aria-label", `${more} more on ${long}`); rest.addEventListener("click", () => jump("day", cell.date));
          pills.append(rest);
        }
        box.append(number, pills);
        if (entries.length) box.append(el("span", "cal-count t-signal", String(entries.length)));
        grid.append(box);
      }
      main.append(grid);
    } else if (nav.view === "day") {
      const { allDay, timed } = dayAgenda(rows, nav.date);
      const list = el("ol", "cal-day");
      const line = (when, row) => { const li = el("li", "cal-day-row"); li.append(el("span", "t-signal cal-day-time", when), pill(row)); return li; };
      for (const row of allDay) list.append(line(row.task ? "Due" : "All day", row));
      for (const row of timed) list.append(line(row.time, row));
      main.append(list);
      if (!allDay.length && !timed.length) main.append(el("p", "t-body empty", "Nothing on this day."));
    } else {
      const year = el("div", "cal-year");
      for (const m of yearMonths(rows, start.slice(0, 4))) {
        const card = el("button", "cal-month-card"); card.type = "button"; card.dataset.month = m.month; card.dataset.focusKey = `calendar-month-${m.month}`;
        card.setAttribute("aria-label", `${m.name}: ${m.total} ${m.total === 1 ? "entry" : "entries"}`);
        card.append(el("span", "t-body strong", m.name), el("span", "t-title cal-month-total", String(m.total)),
          el("span", "t-small cal-month-split", `${m.events} ${m.events === 1 ? "event" : "events"} · ${m.tasks} ${m.tasks === 1 ? "task" : "tasks"}`));
        card.addEventListener("click", () => jump("month", m.month));
        year.append(card);
      }
      main.append(year);
    }
    // On a phone the month grid has no room for words, so the period's
    // entries follow it as a list (css/calendar.css shows this only there).
    const inPeriod = rows.filter(r => r.date && r.date >= start && r.date < end).sort(byWhen);
    if (nav.view === "month" && inPeriod.length) {
      const list = el("ol", "cal-period-list");
      for (const row of inPeriod) { const li = el("li", "cal-day-row"); li.append(el("span", "t-signal cal-day-time", format(row.date, { day: "numeric", month: "short" })), pill(row)); list.append(li); }
      main.append(list);
    }

    // The side: Unscheduled with its questions, the chosen entry, adding.
    const side = el("aside", "cal-side");
    side.setAttribute("aria-label", "Unscheduled entries and details");
    const unscheduled = el("section", "cal-unscheduled calendar-unscheduled");
    unscheduled.append(el("h3", "t-body strong", "Unscheduled"));
    const questions = model.unresolved.filter(w => w.data.status === "clarify" && w.data.prompt);
    for (const w of questions) unscheduled.append(el("p", "t-small cal-question", w.data.prompt));
    const undated = rows.filter(r => !r.date);
    const undatedList = el("ul", "cal-undated");
    for (const row of undated) {
      const li = el("li"); li.append(pill(row));
      if (row.clarification) li.append(el("p", "t-small cal-question", row.clarification));
      undatedList.append(li);
    }
    if (undated.length) unscheduled.append(undatedList);
    else if (!questions.length) unscheduled.append(el("p", "t-meta", "No undated entries."));
    side.append(unscheduled);
    const chosen = rows.find(r => r.id === selected);
    if (chosen) {
      const detail = el("section", "cal-detail"); detail.tabIndex = -1;
      detail.setAttribute("aria-label", `Details of ${chosen.text}`);
      const close = el("button", "btn btn-quiet btn-sm", "Close details"); close.type = "button";
      close.addEventListener("click", () => { selected = null; draw(ctx, ctx.app.snapshot, true); });
      detail.append(item(chosen), close);
      side.append(detail);
    } else side.append(el("p", "t-small cal-hint", "Choose an entry to see its evidence and edit it."));
    if (controls.editable) side.append(editor());
    const proposed = taskChangesElement(snapshot, doc, controls.send, controls.button);
    if (proposed.children.length) side.append(proposed);
    if (d.state === "reviewing" && rows.some(r => r.task))
      side.append(el("p", "t-meta", "Accepting this calendar also confirms the displayed shared task details. Later AI task changes require review."));

    const body = el("div", "cal-body");
    body.append(main, side);
    host.replaceChildren(head, toolbar, legend, body);
    // Back to the control that had the focus; if a day or a month card
    // moved the period and is gone, to the new period's heading, so a
    // keyboard user is not dropped to the top of the page.
    const target = focus ? host.querySelector(`[data-focus-key="${focus}"]`) : null;
    if (target) { target.focus(); if (caret && target.setSelectionRange) target.setSelectionRange(...caret); }
    else if (hadFocus) period.focus();
  }

  registerTool("calendar-view", {
    mount(ctx) {
      ctxRef = ctx;
      host = ctx.$("calendar-view");
      // The canvas card's Open calendar (documents.mjs) bubbles this.
      document.addEventListener("jv:open-calendar", event => {
        chosenId = event.detail?.documentId ?? chosenId; selected = null;
        ctxRef.view("calendar");
      });
    },
    render(ctx, snapshot) {
      if (!host) return;
      let voice = false;
      for (const doc of calendarDocs(snapshot)) if (voiceFocus(seen, doc)) { voice = true; chosenId = doc.id; }
      // Not from inside this render: switching views renders again.
      if (voice && ctx.app.view !== "calendar" && ctx.app.screen === "workspace") queueMicrotask(() => ctx.view("calendar"));
      if (ctx.app.view !== "calendar" || ctx.app.screen !== "workspace") { signature = ""; return; }
      draw(ctx, snapshot);
    },
  });
}
