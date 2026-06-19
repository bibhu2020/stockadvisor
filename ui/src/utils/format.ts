/** Parse a bare UTC string (no Z) or a full ISO string correctly. */
function parseUTC(s: string): Date {
  const iso = s.includes('T') ? s : s.replace(' ', 'T')
  return new Date(iso.endsWith('Z') || /[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z')
}

/** "Jun 18, 2026, 9:30 AM" in the browser's local timezone. */
export function fmtDateTime(utcStr: string | null | undefined): string {
  if (!utcStr) return '—'
  return parseUTC(utcStr).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

/** "Jun 18, 2026" in the browser's local timezone. */
export function fmtDate(utcStr: string | null | undefined): string {
  if (!utcStr) return '—'
  return parseUTC(utcStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}
