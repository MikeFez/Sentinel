import type { Sync } from '../../types';
import { money, parseTime, shortDate } from '../../lib/format';

/** Price at each completed sync, oldest to newest. */
function PriceChart({ syncs }: { syncs: Sync[] }) {
  const points = syncs
    .filter((s) => s.stock_price != null)
    .map((s) => ({ t: parseTime(s.synced_at).getTime(), p: s.stock_price! }))
    .sort((a, b) => a.t - b.t);
  if (points.length < 2) return null;

  const W = 800, H = 140, pad = 6;
  const t0 = points[0].t, t1 = points[points.length - 1].t;
  const lo = Math.min(...points.map((x) => x.p)), hi = Math.max(...points.map((x) => x.p));
  const x = (t: number) => pad + ((t - t0) / (t1 - t0 || 1)) * (W - pad * 2);
  const y = (p: number) => pad + (1 - (p - lo) / (hi - lo || 1)) * (H - pad * 2);
  const d = points.map((pt, i) => `${i ? 'L' : 'M'}${x(pt.t).toFixed(1)},${y(pt.p).toFixed(1)}`).join(' ');
  const up = points[points.length - 1].p >= points[0].p;

  return (
    <figure className="price-chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img"
        aria-label={`Price from ${money(points[0].p)} to ${money(points[points.length - 1].p)}`}>
        <path d={d} fill="none" stroke={up ? 'var(--success)' : 'var(--error)'} strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <figcaption className="muted">
        <span>{shortDate(t0)} · {money(points[0].p)}</span>
        <span>low {money(lo)} · high {money(hi)}</span>
        <span>{shortDate(t1)} · {money(points[points.length - 1].p)}</span>
      </figcaption>
    </figure>
  );
}

export default PriceChart;
