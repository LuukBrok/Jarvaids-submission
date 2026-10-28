/**
 * Dates on notes and task rows (chips.mjs), without a browser.
 *
 * The day is always the session's day: the same instant is "today" in one
 * zone and "overdue" in another, and the device's own zone must not decide.
 *
 *     node --test tests/chips-unit.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { collectingCalendar, dateChip, EVENT_TEXT_MAX, eventText, noteEvents, zoneDay } from "../chips.mjs";

// 26 October 2026, 23:30 UTC: already the 27th in Amsterdam (UTC+1 after the
// clocks went back on the 25th), still the 26th in New York and in UTC.
const LATE = new Date(Date.UTC(2026, 9, 26, 23, 30));

test("today is the session's day, not the device's or UTC's", () => {
  assert.equal(zoneDay("Europe/Amsterdam", LATE), "2026-10-27");
  assert.equal(zoneDay("America/New_York", LATE), "2026-10-26");
  assert.equal(zoneDay("UTC", LATE), "2026-10-26");
});

test("an unknown or missing zone falls back to UTC, as the server does", () => {
  assert.equal(zoneDay("Not/A_Zone", LATE), "2026-10-26");
  assert.equal(zoneDay("", LATE), "2026-10-26");
  assert.equal(zoneDay(undefined, LATE), "2026-10-26");
});

test("the same date is overdue, today or plain depending on the session's zone", () => {
  const event = { date: "2026-10-26", time: "", done: false };
  assert.equal(dateChip(event, "Europe/Amsterdam", LATE).tone, "overdue");
  assert.equal(dateChip(event, "America/New_York", LATE).tone, "today");
  assert.equal(dateChip({ ...event, date: "2026-10-28" }, "Europe/Amsterdam", LATE).tone, "plain");
});

test("the chip says its state in words, so colour is never the only signal", () => {
  const overdue = dateChip({ date: "2026-10-20" }, "Europe/Amsterdam", LATE);
  assert.equal(overdue.text, "Overdue · Tue 20 Oct");
  assert.equal(overdue.title, "Tuesday 20 October 2026, overdue");
  const today = dateChip({ date: "2026-10-27", time: "14:00" }, "Europe/Amsterdam", LATE);
  assert.deepEqual([today.tone, today.text, today.title], ["today", "Today 14:00", "Tuesday 27 October 2026 at 14:00, today"]);
  const later = dateChip({ date: "2026-10-30", time: "09:30" }, "Europe/Amsterdam", LATE);
  assert.deepEqual([later.tone, later.text], ["plain", "Fri 30 Oct 09:30"]);
});

test("a date in another year names the year", () => {
  assert.equal(dateChip({ date: "2027-01-04" }, "UTC", LATE).text, "Mon 4 Jan 2027");
});

test("anything done is plain, however late", () => {
  const done = dateChip({ date: "2026-10-01", done: true }, "UTC", LATE);
  assert.deepEqual([done.tone, done.text, done.title], ["plain", "Thu 1 Oct", "Thursday 1 October 2026, done"]);
  assert.equal(dateChip({ date: "2026-10-26", done: true }, "UTC", LATE).tone, "plain");
});

test("no exact date, no chip: a spoken phrase is never turned into a date here", () => {
  for (const date of ["", "Friday", "2026-10", "26/10/2026", undefined, null])
    assert.equal(dateChip({ date }, "UTC", LATE), null, String(date));
});

const calendar = (id, state, entryIds) => ({ id, kind: "command_document", revision: 1,
  data: { document_type: "calendar", state, entry_ids: entryIds, task_ids: [] } });
const event = (id, extra = {}) => ({ id, kind: "command_entry", revision: 1,
  data: { entry_type: "calendar_event", text: id, date: "", time: "", done: false, removed: false, ...extra } });

test("a note's events are the live ones linked to it, soonest first and undated last", () => {
  const snapshot = { records: [
    calendar("c1", "collecting", ["late", "soon", "undated", "removed", "other"]),
    calendar("c2", "cancelled", ["cancelled"]),
    event("late", { note_id: "n1", date: "2026-11-02" }),
    event("soon", { note_id: "n1", date: "2026-10-28", time: "09:00" }),
    event("undated", { note_id: "n1" }),
    event("removed", { note_id: "n1", date: "2026-10-27", removed: true }),
    event("cancelled", { note_id: "n1", date: "2026-10-27" }),
    event("other", { note_id: "n2", date: "2026-10-27" }),
    event("orphan", { note_id: "n1", date: "2026-10-27" }),
  ] };
  assert.deepEqual(noteEvents(snapshot, "n1").map(e => e.record.id), ["soon", "late", "undated"]);
  assert.equal(noteEvents(snapshot, "n1")[0].calendar.id, "c1");
  assert.deepEqual(noteEvents(snapshot, "n3"), []);
});

test("new events go to the newest collecting calendar, and to none when nothing collects", () => {
  assert.equal(collectingCalendar({ records: [calendar("a", "collecting", []), calendar("b", "reviewing", []),
    calendar("c", "collecting", []), calendar("d", "accepted", [])] }).id, "c");
  assert.equal(collectingCalendar({ records: [calendar("b", "reviewing", []), calendar("d", "cancelled", [])] }), null);
  assert.equal(collectingCalendar({ records: [{ id: "t", kind: "command_document", data: { document_type: "todo", state: "collecting" } }] }), null);
});

test("a note's text fits the server's event limit", () => {
  assert.equal(eventText("  Book the lab  "), "Book the lab");
  const long = eventText("x".repeat(EVENT_TEXT_MAX + 50));
  assert.equal(long.length, EVENT_TEXT_MAX);
  assert(long.endsWith("…"));
  assert.equal(eventText("y".repeat(EVENT_TEXT_MAX)).length, EVENT_TEXT_MAX);
});
