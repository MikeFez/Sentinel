import { TrendingUp } from 'lucide-react';
import type { AnalystRatings as AnalystRatingsType } from '../../types';
import './AnalystRatings.css';

const LEVELS = [
  { key: 'strongBuy', label: 'Strong buy', score: 5 },
  { key: 'buy', label: 'Buy', score: 4 },
  { key: 'hold', label: 'Hold', score: 3 },
  { key: 'sell', label: 'Sell', score: 2 },
  { key: 'strongSell', label: 'Strong sell', score: 1 },
] as const;

/** Average rating on a 1 (strong sell) to 5 (strong buy) scale, named like the usual consensus labels. */
function consensus(mean: number): { text: string; tone: string } {
  if (mean >= 4.5) return { text: 'Strong buy', tone: 'up' };
  if (mean >= 3.5) return { text: 'Buy', tone: 'up' };
  if (mean >= 2.5) return { text: 'Hold', tone: 'ar-tone-hold' };
  if (mean >= 1.5) return { text: 'Sell', tone: 'down' };
  return { text: 'Strong sell', tone: 'down' };
}

function AnalystRatings({ ratings }: { ratings: AnalystRatingsType }) {
  const rows = LEVELS.map((l) => ({ ...l, count: ratings[l.key] ?? 0 }));
  const total = rows.reduce((s, r) => s + r.count, 0);
  if (total === 0) return null;

  const mean = rows.reduce((s, r) => s + r.score * r.count, 0) / total;
  const c = consensus(mean);
  const most = Math.max(...rows.map((r) => r.count));

  return (
    <div className="card analyst-ratings">
      <h2>
        <TrendingUp size={15} /> Analyst ratings
        <span className="muted ar-total">{total} analysts</span>
      </h2>
      <div className="ar-consensus">
        <span className={`ar-consensus-value ${c.tone}`}>{c.text}</span>
        <span className="muted num" title="Average rating: 5 = strong buy, 1 = strong sell">{mean.toFixed(1)} / 5</span>
      </div>
      <div className="ar-rows">
        {rows.map((r) => (
          <div key={r.key} className="ar-row">
            <span className="ar-label">{r.label}</span>
            <div className="ar-track">
              {/* Bars are scaled to the largest group so small differences stay visible */}
              <div className={`ar-bar ar-${r.key}`} style={{ width: `${(r.count / most) * 100}%` }} />
            </div>
            <span className="ar-count num">{r.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AnalystRatings;
