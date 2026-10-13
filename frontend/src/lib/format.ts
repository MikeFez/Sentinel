// One place for how numbers and times look across the app.

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const usdWhole = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

export const money = (n: number | null | undefined, whole = false) =>
  n == null ? '—' : (whole ? usdWhole : usd).format(n);

export const signedMoney = (n: number) => `${n >= 0 ? '+' : '−'}${usd.format(Math.abs(n))}`;

export const pct = (n: number | null | undefined) =>
  n == null ? '—' : `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(2)}%`;

export const num = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('en-US'));

/** EPS with enough precision that close values don't look equal (e.g. -0.080 vs -0.077). */
export const eps = (v: number) => v.toFixed(Math.abs(v) < 1 ? 3 : 2);

export const direction = (n: number | null | undefined) => (n == null ? '' : n >= 0 ? 'up' : 'down');

/** Parse a server timestamp. Older API responses had no offset; those are UTC. */
export function parseTime(value: string | number): Date {
  if (typeof value === 'number') return new Date(value < 1e12 ? value * 1000 : value);
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value);
  return new Date(hasZone || value.length <= 10 ? value : `${value}Z`);
}

/** "just now", "5m ago", "3h ago", "2d ago", "4mo ago", "1y ago" */
export function ago(value: string | number | null | undefined): string {
  if (value == null) return 'never';
  const s = Math.max(0, (Date.now() - parseTime(value).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 86400 * 30) return `${Math.floor(s / 86400)}d ago`;
  if (s < 86400 * 365) return `${Math.floor(s / (86400 * 30))}mo ago`;
  return `${Math.floor(s / (86400 * 365))}y ago`;
}

export const hoursSince = (value: string | number) => (Date.now() - parseTime(value).getTime()) / 3_600_000;

/** Calendar date ("2026-11-04") → "Nov 4" / "Nov 4, 2027" */
export function shortDate(value: string | number): string {
  const d = typeof value === 'string' && value.length === 10 ? new Date(`${value}T00:00:00`) : parseTime(value);
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', ...(sameYear ? {} : { year: 'numeric' }) });
}

/** Days from today to a calendar date (negative = past). */
export function daysUntil(isoDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(`${isoDate}T00:00:00`).getTime() - today.getTime()) / 86_400_000);
}

export function inDays(isoDate: string): string {
  const d = daysUntil(isoDate);
  if (d === 0) return 'today';
  if (d === 1) return 'tomorrow';
  if (d < 0) return `${-d}d ago`;
  return `in ${d}d`;
}
