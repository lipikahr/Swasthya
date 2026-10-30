/** Local-calendar day helpers. Never derive a day from toISOString(), which is UTC. */

function pad(value: number) {
  return String(value).padStart(2, "0");
}

export function toIsoDay(value: Date) {
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}

export function localIsoDay(now: Date = new Date()) {
  return toIsoDay(now);
}

export function parseDay(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day, 12, 0, 0, 0);
}

export function shiftDay(iso: string, days: number) {
  const value = parseDay(iso);
  value.setDate(value.getDate() + days);
  return toIsoDay(value);
}

export function startOfWeek(iso: string) {
  const value = parseDay(iso);
  const weekday = (value.getDay() + 6) % 7;
  value.setDate(value.getDate() - weekday);
  return toIsoDay(value);
}

export function shiftMonth(iso: string, months: number) {
  const value = parseDay(iso);
  const day = value.getDate();
  value.setDate(1);
  value.setMonth(value.getMonth() + months);
  const last = new Date(value.getFullYear(), value.getMonth() + 1, 0).getDate();
  value.setDate(Math.min(day, last));
  return toIsoDay(value);
}

export function monthBounds(iso: string) {
  const value = parseDay(iso);
  const start = new Date(value.getFullYear(), value.getMonth(), 1, 12);
  const end = new Date(value.getFullYear(), value.getMonth() + 1, 0, 12);
  return { start: toIsoDay(start), end: toIsoDay(end) };
}

/** Monday-first calendar cells for the month containing `iso`. Null marks a leading or trailing blank. */
export function monthCells(iso: string): Array<string | null> {
  const { start, end } = monthBounds(iso);
  const first = parseDay(start);
  const lead = (first.getDay() + 6) % 7;
  const cells: Array<string | null> = Array.from({ length: lead }, () => null);
  const last = parseDay(end).getDate();
  for (let day = 1; day <= last; day += 1) cells.push(shiftDay(start, day - 1));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function formatLong(iso: string) {
  return parseDay(iso).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export function formatMonth(iso: string) {
  return parseDay(iso).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export function formatShort(iso: string) {
  return parseDay(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function weekdayShort(iso: string) {
  return parseDay(iso).toLocaleDateString(undefined, { weekday: "short" });
}
