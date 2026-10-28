/**
 * The Calendar view's pure parts, without a browser: the month and week
 * grids, entries by day and per cell, the day list by time, the year's
 * counts, which calendar is shown, the honest empty state, when a voice
 * command brings the view forward, and how a pill is marked.
 *
 *     node --test tests/calendar-view-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { MAKE_CALENDAR, MONTH_CELL_PILLS, calendarDocs, cellEntries, dayAgenda, emptyState, entriesByDay, gridDays,
  pickCalendar, voiceFocus, yearMonths } from "../calendar-view.mjs";
import { calendarNav, calendarRows, periodRange, pillModel, todayIn, upcoming } from "../calendar.mjs";

const entry = (id, data) => ({ id, kind: "command_entry", revision: 1, data: { removed: false, status: "provisional", origin: "model", source_refs: [], ...data } });
const doc = (id, data = {}) => ({ id, kind: "command_document", revision: 1,
  data: { document_type: "calendar", state: "collecting", entry_ids: ["e1", "e2", "e3", "e4"], task_ids: ["t1"], timezone: "Europe/Amsterdam",
    calendar_view: "month", calendar_date: "2026-10-19", calendar_focus_revision: 0, calendar_focus_origin: "initial", ...data } });
const snapshot = { records: [
  doc("cal"),
  entry("e1", { text: "Prototype review", date: "2026-10-20", time: "14:00" }),
  entry("e2", { text: "Launch party", date: "", date_phrase: "undecided" }),
  entry("e3", { text: "Team lunch", date: "2026-10-20", time: "12:30", origin: "human" }),
  entry("e4", { text: "Design expo", date: "2026-11-02", time: "", status: "accepted" }),
  entry("t1", { entry_type: "task", text: "Prepare questions", deadline_date: "2026-10-20", owner: "Julie", done: true }),
  entry("gone", { text: "Removed", date: "2026-10-20", removed: true }),
] };
const rows = calendarRows(snapshot, snapshot.records[0]);

test("a month is six whole weeks from the Monday on or before the 1st", () => {
  const days = gridDays("month", "2026-10-19", "2026-10-20");
  assert.equal(days.length, 42);
  assert.equal(days[0].date, "2026-09-28");
  assert.equal(days[0].outside, true);
  assert.equal(days.find(d => d.date === "2026-10-01").outside, false);
  assert.equal(days.at(-1).date, "2026-11-08");
  assert.equal(days.find(d => d.today).date, "2026-10-20");
  assert.equal(days.find(d => d.current).date, "2026-10-19");
});

test("a week runs Monday to Sunday, and day and year have no grid", () => {
  const days = gridDays("week", "2026-10-22");
  assert.deepEqual(days.map(d => d.date), ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25"]);
  assert(days.every(d => !d.outside));
  assert.deepEqual(gridDays("day", "2026-10-22"), []);
  assert.deepEqual(gridDays("year", "2026-10-22"), []);
});

test("a month grid crosses a year end without shifting a day", () => {
  const days = gridDays("month", "2027-01-15");
  assert.equal(days[0].date, "2026-12-28");
  assert.equal(days.filter(d => !d.outside).length, 31);
});

test("rows leave out removed entries and take a task's deadline as its date", () => {
  assert.deepEqual(rows.map(r => r.id).sort(), ["e1", "e2", "e3", "e4", "t1"]);
  assert.equal(rows.find(r => r.id === "t1").date, "2026-10-20");
  assert.equal(rows.find(r => r.id === "t1").task, true);
});

test("entries by day are in reading order: untimed first, then by time", () => {
  const day = entriesByDay(rows).get("2026-10-20").map(r => r.text);
  assert.deepEqual(day, ["Prepare questions", "Team lunch", "Prototype review"]);
  assert.equal(entriesByDay(rows).has(""), false, "undated entries are not on any day");
});

test("a month cell shows three pills, or two and how many more", () => {
  const three = [1, 2, 3];
  assert.deepEqual(cellEntries(three), { shown: three, more: 0 });
  assert.deepEqual(cellEntries([1, 2, 3, 4, 5]), { shown: [1, 2], more: 3 });
  assert.equal(MONTH_CELL_PILLS, 3);
});

test("a day is a list by time, with deadlines and all-day entries first", () => {
  const { allDay, timed } = dayAgenda(rows, "2026-10-20");
  assert.deepEqual(allDay.map(r => r.text), ["Prepare questions"]);
  assert.deepEqual(timed.map(r => r.time), ["12:30", "14:00"]);
});

test("a year is twelve months with their counts split by kind", () => {
  const months = yearMonths(rows, "2026");
  assert.equal(months.length, 12);
  assert.deepEqual(months[9], { month: "2026-10-01", name: "October", events: 2, tasks: 1, total: 3 });
  assert.equal(months[10].total, 1);
  assert.equal(months.reduce((n, m) => n + m.total, 0), 4, "the undated entry is in no month");
});

test("a pill takes its accent from its kind, an owner only on a task, and the machine mark only for an unaccepted interpretation", () => {
  const task = pillModel(rows.find(r => r.id === "t1"));
  assert.equal(task.kind, "task");
  assert.equal(task.owner, "Julie");
  assert.equal(task.done, true);
  assert.equal(task.machine, true);
  assert.match(task.label, /^Linked task: Prepare questions, owner Julie, complete/);
  const event = pillModel(rows.find(r => r.id === "e1"));
  assert.equal(event.kind, "event");
  assert.equal(event.owner, "");
  assert.match(event.label, /^Event: 14:00, Prototype review/);
  assert.equal(pillModel(rows.find(r => r.id === "e3")).machine, false, "a person's entry is not the machine's");
  assert.equal(pillModel(rows.find(r => r.id === "e4")).machine, false, "an accepted entry is settled");
});

test("the card's summary lists the next three dated entries from today", () => {
  assert.deepEqual(upcoming(rows, "2026-10-20").map(r => r.text), ["Prepare questions", "Team lunch", "Prototype review"]);
  assert.deepEqual(upcoming(rows, "2026-10-21").map(r => r.text), ["Design expo"]);
  assert.deepEqual(upcoming(rows, "2026-12-01"), []);
});

test("today is the meeting's date, not the browser's", () => {
  const late = new Date("2026-10-20T23:30:00Z");
  assert.equal(todayIn("Europe/Amsterdam", late), "2026-10-21");
  assert.equal(todayIn("UTC", late), "2026-10-20");
});

test("the period a view shows is half open", () => {
  assert.deepEqual(periodRange("week", "2026-10-22"), { start: "2026-10-19", end: "2026-10-26" });
  assert.deepEqual(periodRange("year", "2026-10-22"), { start: "2026-01-01", end: "2027-01-01" });
});

test("the calendar shown is the chosen one, else the newest open, else accepted, else newest", () => {
  const old = doc("old", { state: "cancelled" }), accepted = doc("acc", { state: "accepted" }), open = doc("open", { state: "reviewing" });
  assert.equal(pickCalendar([old, accepted, open]).id, "open");
  assert.equal(pickCalendar([old, accepted]).id, "acc");
  assert.equal(pickCalendar([old]).id, "old");
  assert.equal(pickCalendar([old, accepted, open], "old").id, "old");
  assert.equal(pickCalendar([]), null);
  assert.deepEqual(calendarDocs({ records: [old, { id: "todo", kind: "command_document", data: { document_type: "todo" } }] }).map(d => d.id), ["old"]);
});

test("the empty state offers the typed command only where typed commands run", () => {
  const ai = { available: true, types: ["todo", "requirements", "calendar"], notice: "" };
  assert.equal(emptyState({ command_ai: ai, automatic_workspace: true }).kind, "button");
  const spoken = emptyState({ command_ai: ai });
  assert.equal(spoken.kind, "spoken");
  assert(spoken.text.includes(MAKE_CALENDAR));
  assert.equal(MAKE_CALENDAR, "Hey Jarvaids, make a calendar");
});

test("with the command interpreter off, the empty state says so and offers nothing", () => {
  const off = emptyState({ command_ai: { available: false, notice: "Set ANTHROPIC_API_KEY to enable it." }, automatic_workspace: true });
  assert.equal(off.kind, "off");
  assert.match(off.text, /command interpreter is off/);
  assert.match(off.text, /ANTHROPIC_API_KEY/);
  assert.equal(emptyState({}).kind, "off", "an older server without command_ai offers nothing");
  assert.equal(emptyState({ command_ai: { available: true, types: ["todo"] }, automatic_workspace: true }).kind, "off");
});

test("a voice focus brings the view forward only when it is new to this screen", () => {
  const seen = new Map();
  assert.equal(voiceFocus(seen, doc("c", { calendar_focus_revision: 1, calendar_focus_origin: "voice" })), false, "first sight only records");
  assert.equal(voiceFocus(seen, doc("c", { calendar_focus_revision: 1, calendar_focus_origin: "voice" })), false, "the same focus again");
  assert.equal(voiceFocus(seen, doc("c", { calendar_focus_revision: 2, calendar_focus_origin: "interpretation" })), false, "an interpretation never pulls the screen");
  assert.equal(voiceFocus(seen, doc("c", { calendar_focus_revision: 3, calendar_focus_origin: "voice" })), true);
});

test("a voice view command overrides local navigation; an interpretation does not", () => {
  const state = {};
  const nav = calendarNav(state, doc("c").data);
  assert.deepEqual([nav.view, nav.date], ["month", "2026-10-19"]);
  Object.assign(nav, { view: "day", date: "2026-12-01", touched: true });
  calendarNav(state, doc("c", { calendar_view: "year", calendar_focus_revision: 1, calendar_focus_origin: "interpretation" }).data);
  assert.equal(nav.view, "day", "a person's navigation stays");
  calendarNav(state, doc("c", { calendar_view: "week", calendar_date: "2026-10-22", calendar_focus_revision: 2, calendar_focus_origin: "voice" }).data);
  assert.deepEqual([nav.view, nav.date, nav.touched], ["week", "2026-10-22", false]);
});
