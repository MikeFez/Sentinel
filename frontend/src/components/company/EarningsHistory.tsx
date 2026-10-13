import { CalendarClock } from 'lucide-react';
import type { EarningsDate, EarningsQuarter } from '../../types';
import { daysUntil, eps, inDays, shortDate } from '../../lib/format';

/** Reported vs estimated EPS for the last few quarters, with the next report date in the header. */
function EarningsHistory({ quarters, dates }: { quarters: EarningsQuarter[]; dates: EarningsDate[] }) {
  const rows = quarters.filter((q) => q.actual != null);
  const next = dates.filter((d) => daysUntil(d.date) >= 0).sort((a, b) => a.date.localeCompare(b.date))[0];
  if (!rows.length && !next) return null;
  const beats = rows.filter((q) => (q.surprisePercent ?? 0) >= 0 && q.estimate != null).length;

  return (
    <div className="card">
      <h2>Earnings {rows.length > 0 && <span className="muted eh-summary">beat {beats} of {rows.length}</span>}</h2>
      {next && (
        <div className="eh-next">
          <CalendarClock size={14} />
          <span>Next report <strong>{shortDate(next.date)}</strong> <span className="muted">({inDays(next.date)})</span></span>
          {next.epsEstimate != null && <span className="muted num eh-next-est">est. EPS {eps(next.epsEstimate)}</span>}
        </div>
      )}
      {rows.length > 0 && (
        <table className="data-table">
          <thead><tr><th>Quarter</th><th className="r">EPS</th><th className="r">Estimate</th><th className="r">Surprise</th></tr></thead>
          <tbody>
            {rows.map((q) => {
              const s = q.surprisePercent;
              return (
                <tr key={`${q.year}-${q.quarter}-${q.period}`}>
                  <td>{q.quarter ? `Q${q.quarter} ${q.year}` : q.period}</td>
                  <td className="r num">{eps(q.actual!)}</td>
                  <td className="r num muted">{q.estimate != null ? eps(q.estimate) : '—'}</td>
                  <td className={`r num ${s == null ? 'muted' : s >= 0 ? 'up' : 'down'}`}>
                    {s == null ? '—' : `${s >= 0 ? 'beat +' : 'miss −'}${Math.abs(s).toFixed(1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default EarningsHistory;
