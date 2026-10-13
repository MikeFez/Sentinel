import { parseTime } from './format';

// When the News page was last left (everything older counts as seen), and per company when its
// News tab was last opened. Per browser; without storage nothing is ever marked unread.
const LAST_VISIT_KEY = 'sentinel.news.lastVisit';
const COMPANY_KEY = 'sentinel.news.seenByCompany';

export function readLastVisit(): number {
  try {
    return Number(localStorage.getItem(LAST_VISIT_KEY)) || 0;
  } catch {
    return 0;
  }
}

export function readSeenByCompany(): Record<string, number> {
  try {
    const v = JSON.parse(localStorage.getItem(COMPANY_KEY) ?? '{}');
    return v && typeof v === 'object' ? v : {};
  } catch {
    return {};
  }
}

/** Mark all news (companyId null) or one company's news as seen now. */
export function writeSeen(companyId: string | null, now = Date.now()) {
  try {
    if (companyId) {
      localStorage.setItem(COMPANY_KEY, JSON.stringify({ ...readSeenByCompany(), [companyId]: now }));
    } else {
      localStorage.setItem(LAST_VISIT_KEY, String(now));
      localStorage.removeItem(COMPANY_KEY); // the global mark now covers every company
    }
  } catch {
    /* private mode: nothing is marked */
  }
}

export function hasUnreadNews(latestNewsAt: string | null | undefined, lastVisit: number, seenAt: number | undefined): boolean {
  const seen = Math.max(lastVisit, seenAt ?? 0);
  return !!latestNewsAt && seen > 0 && parseTime(latestNewsAt).getTime() > seen;
}
