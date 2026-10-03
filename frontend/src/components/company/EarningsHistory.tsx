import type { EarningsQuarter } from '../../types';

// Enough precision that close values don't look equal (e.g. -0.080 vs -0.077)
const eps = (v: number) => v.toFixed(Math.abs(v) < 1 ? 3 : 2);

/** Reported vs estimated EPS for the last few quarters. */
function EarningsHistory({ quarters }: { quarters: EarningsQuarter[] }) {
  const rows = quarters.filter((q) => q.actual != null);
  if (!rows.length) return null;
  const beats = rows.filter((q) => (q.surprisePercent ?? 0) >= 0 && q.estimate != null).length;

  return (
    <div className="card">
      <h2>Earnings history <span className="muted eh-summary">beat {beats} of {rows.length}</span></h2>
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
    </div>
  );
}

export default EarningsHistory;
