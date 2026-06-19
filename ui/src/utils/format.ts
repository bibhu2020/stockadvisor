/**
 * Parse a datetime string that the API may return in several forms:
 *   "2026-06-19T14:45:00.000Z"        — already UTC ISO, use as-is
 *   "2026-06-19T14:45:00.000+00:00"   — explicit UTC offset, use as-is
 *   "2026-06-19T14:45:00.123456"      — ISO without TZ: treat as UTC
 *   "2026-06-19 14:45:00.123456"      — SQLite / bare PG string: treat as UTC
 *
 * The pg-type-parser fix in app.module.ts handles this on the Postgres path,
 * but we stay defensive here for local SQLite dev and any edge cases.
 */
function parseUTC(s: string): Date {
  if (!s) return new Date(NaN)
  // Normalise space separator → T
  const iso = s.includes('T') ? s : s.replace(' ', 'T')
  // If there is already an explicit timezone (+XX:XX or Z) trust it
  if (iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso)) return new Date(iso)
  // Otherwise the value is a bare UTC timestamp — append Z
  return new Date(iso + 'Z')
}

/** "Jun 19, 2026, 9:45 AM" in the browser's local timezone. */
export function fmtDateTime(utcStr: string | null | undefined): string {
  if (!utcStr) return '—'
  return parseUTC(utcStr).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

/** "Jun 19, 2026" in the browser's local timezone. */
export function fmtDate(utcStr: string | null | undefined): string {
  if (!utcStr) return '—'
  return parseUTC(utcStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}
