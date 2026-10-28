/**
 * Dates on notes and task rows: the pure rules, without a page.
 *
 * Every date here is a YYYY-MM-DD string in the session's IANA time zone, as
 * the server stores it (calendar_dates.py). "Today" is worked out in that
 * zone, never the device's own, because a laptop set to another zone would
 * otherwise call a task overdue that the room still has today to finish.
 * The comparison is on strings, so no date ever moves across a zone line.
 *
 *     node --test tests/chips-unit.mjs
 */

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
/** The server's event text limit (calendar_service.py, text 800). */
export const EVENT_TEXT_MAX = 800;

/** Today's date in `zone`, as YYYY-MM-DD. An unknown zone falls back to UTC,
 * which is what the server assumes for a session without one; it never falls
 * back to the device's zone. */
export function zoneDay(zone, now = new Date()) {
  let format;
  try { format = new Intl.DateTimeFormat("en-GB", { timeZone: zone || "UTC", year: "numeric", month: "2-digit", day: "2-digit" }); }
  catch { format = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", year: "numeric", month: "2-digit", day: "2-digit" }); }
  const parts = Object.fromEntries(format.formatToParts(now).map(p => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** A calendar date drawn as words. Noon UTC, formatted in UTC, so the day
 * printed is the day stored (calendar.mjs uses the same rule). */
function words(day, options) {
  const parts = new Intl.DateTimeFormat("en-GB", { ...options, timeZone: "UTC" }).formatToParts(new Date(`${day}T12:00:00Z`));
  return parts.filter(p => p.type !== "literal").map(p => p.value).join(" ");
}

/**
 * The chip for something with a date: {tone, text, title}, or null when
 * there is no exact date to show.
 *
 *   overdue  the date is before today in the session's zone and it is not
 *            done: the coral role, and the word "Overdue" in the chip
 *   today    the date is today and it is not done: the yellow role, "Today"
 *   plain    anything else, including anything done: no fill
 *
 * The word is always in the chip, so the hue is never the only signal.
 */
export function dateChip({ date = "", time = "", done = false } = {}, zone, now = new Date()) {
  if (typeof date !== "string" || !ISO_DAY.test(date)) return null;
  const today = zoneDay(zone, now);
  const tone = done ? "plain" : date < today ? "overdue" : date === today ? "today" : "plain";
  const sameYear = date.slice(0, 4) === today.slice(0, 4);
  const short = date === today ? "Today" : words(date, { weekday: "short", day: "numeric", month: "short", ...(sameYear ? {} : { year: "numeric" }) });
  const at = time ? ` ${time}` : "";
  const text = tone === "overdue" ? `Overdue · ${short}${at}` : `${short}${at}`;
  const long = words(date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }) + (time ? ` at ${time}` : "");
  const state = tone === "overdue" ? ", overdue" : tone === "today" ? ", today" : done ? ", done" : "";
  return { tone, text, title: `${long}${state}` };
}

/** The calendar documents that can still show an event: not cancelled. */
function liveCalendars(records) {
  const byEvent = new Map();
  for (const doc of records)
    if (doc.kind === "command_document" && doc.data.document_type === "calendar" && doc.data.state !== "cancelled")
      for (const id of doc.data.entry_ids ?? []) byEvent.set(id, doc);
  return byEvent;
}

/** The calendar events made from a note that are still in a calendar, the
 * soonest first and undated last: [{record, calendar}]. A removed event, or
 * one in a cancelled calendar, is no longer the note's date. */
export function noteEvents(snapshot, noteId) {
  const records = snapshot?.records ?? [];
  const calendars = liveCalendars(records);
  const key = r => `${r.data.date || "9999-99-99"} ${r.data.time || ""}`;
  return records.filter(r => r.kind === "command_entry" && r.data.entry_type === "calendar_event" &&
      r.data.note_id === noteId && !r.data.removed && calendars.has(r.id))
    .sort((a, b) => key(a).localeCompare(key(b)))
    .map(record => ({ record, calendar: calendars.get(record.id) }));
}

/** The calendar a new event from a note goes into: the newest one that is
 * collecting, or null. Making a calendar is the planning command's job. */
export function collectingCalendar(snapshot) {
  return (snapshot?.records ?? []).filter(r => r.kind === "command_document" &&
    r.data.document_type === "calendar" && r.data.state === "collecting").at(-1) ?? null;
}

/** A note's text as an event's text, within the server's limit. */
export function eventText(text) {
  const value = String(text ?? "").trim();
  return value.length <= EVENT_TEXT_MAX ? value : `${value.slice(0, EVENT_TEXT_MAX - 1)}…`;
}

/** The chip element: mono meta type, a fill only for overdue and today.
 * Built here so a note and a task row draw the same chip. */
export function dateChipElement(chip) {
  const el = document.createElement("span");
  el.className = "date-chip";
  el.dataset.tone = chip.tone;
  el.textContent = chip.text;
  el.title = chip.title;
  el.setAttribute("aria-label", chip.title);
  return el;
}
