import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { getPriceHistory, type DailyPrice } from '../../api/client';
import type { SentimentType, Sync } from '../../types';
import { money, parseTime, pct } from '../../lib/format';
import './CallChart.css';

const DAY = 86_400_000;
// Days without a price longer than this break the line: no data, not a straight move
const GAP_DAYS = 10;
const H = 220;
const M = { top: 12, right: 12, bottom: 24, left: 52 };
const RANGES = [
  { id: '3m', label: '3M', days: 92 },
  { id: '1y', label: '1Y', days: 366 },
  { id: 'all', label: 'All', days: Infinity },
] as const;
type RangeId = typeof RANGES[number]['id'];

// Shape is the second channel beside color, so calls read without relying on red vs. green
const SHAPE_LABEL: Record<SentimentType, string> = { bullish: 'Bullish', bearish: 'Bearish', mixed: 'Mixed', neutral: 'Neutral' };

function Marker({ s, x, y, r = 5 }: { s: SentimentType; x: number; y: number; r?: number }) {
  const cls = `cc-marker cc-${s}`;
  if (s === 'bullish') return <path className={cls} d={`M${x},${y - r - 1} L${x + r + 1},${y + r} L${x - r - 1},${y + r} Z`} />;
  if (s === 'bearish') return <path className={cls} d={`M${x},${y + r + 1} L${x + r + 1},${y - r} L${x - r - 1},${y - r} Z`} />;
  if (s === 'mixed') return <path className={cls} d={`M${x},${y - r - 1} L${x + r + 1},${y} L${x},${y + r + 1} L${x - r - 1},${y} Z`} />;
  return <circle className={cls} cx={x} cy={y} r={r} />;
}

interface Call { t: number; price: number; sentiment: SentimentType }

/** "Nice" tick values covering lo..hi (about `count` of them). */
function ticks(lo: number, hi: number, count = 4): number[] {
  const span = hi - lo || Math.abs(hi) || 1;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out = [];
  // Start at or below the lowest value and end at or above the highest, so no mark sits outside the axis
  for (let v = Math.floor(lo / step) * step; v < hi + step - 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/**
 * Price over time with each AI sentiment call marked where it was made: a visual track record.
 * Prices are daily closes (plus today's latest quote); calls are each day's last analysis.
 */
function CallChart({ companyId, syncs, live }: { companyId: string; syncs: Sync[]; live: { price: number; at: string } | null }) {
  const [prices, setPrices] = useState<DailyPrice[] | null>(null);
  const [range, setRange] = useState<RangeId>('all');
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getPriceHistory(companyId).then(setPrices).catch(() => setPrices([]));
  }, [companyId, syncs.length]);

  // Re-attach when the element changes (the loading placeholder is replaced by the plot)
  const loaded = prices !== null;
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, [loaded]);

  const { points, calls } = useMemo(() => {
    const pts = (prices ?? []).map((p) => ({ t: new Date(`${p.day}T16:00:00-04:00`).getTime(), price: p.price }));
    if (live) {
      const t = parseTime(live.at).getTime();
      if (!pts.length || t > pts[pts.length - 1].t) pts.push({ t, price: live.price });
    }
    const byDay = new Map<string, Call>(); // the day's last call, like the scorecard
    for (const s of [...syncs].sort((a, b) => a.synced_at.localeCompare(b.synced_at))) {
      if (s.status !== 'completed' || !s.ai_sentiment || s.stock_price == null) continue;
      const t = parseTime(s.synced_at).getTime();
      byDay.set(new Date(t).toDateString(), { t, price: s.stock_price, sentiment: s.ai_sentiment });
    }
    return { points: pts, calls: [...byDay.values()] };
  }, [prices, syncs, live]);

  // The measured box is always rendered, so its width is known by the time the prices arrive
  if (prices === null || points.length < 2) {
    return (
      <div ref={boxRef} className="call-chart call-chart-empty muted">
        {prices === null ? 'Loading prices…' : 'Not enough price history for a chart yet.'}
      </div>
    );
  }

  const days = RANGES.find((r) => r.id === range)!.days;
  const end = points[points.length - 1].t;
  const start = Math.max(points[0].t, end - days * DAY);
  const shown = points.filter((p) => p.t >= start);
  const shownCalls = calls.filter((c) => c.t >= start && c.t <= end);
  const all = [...shown.map((p) => p.price), ...shownCalls.map((c) => c.price)];
  const yt = ticks(Math.min(...all), Math.max(...all));
  const lo = yt[0], hi = yt[yt.length - 1];

  const w = Math.max(width, 280);
  const x = (t: number) => M.left + ((t - start) / (end - start || 1)) * (w - M.left - M.right);
  const y = (p: number) => M.top + (1 - (p - lo) / (hi - lo || 1)) * (H - M.top - M.bottom);

  // Line segments, broken across gaps in the data
  const segments: string[] = [];
  let d = '';
  shown.forEach((p, i) => {
    const gap = i > 0 && p.t - shown[i - 1].t > GAP_DAYS * DAY;
    if (gap && d) { segments.push(d); d = ''; }
    d += `${d ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.price).toFixed(1)}`;
  });
  if (d) segments.push(d);
  // A point with no neighbor on either side (between gaps) draws no line; give it a dot
  const lone = shown.filter((p, i) => {
    const before = i > 0 && p.t - shown[i - 1].t <= GAP_DAYS * DAY;
    const after = i < shown.length - 1 && shown[i + 1].t - p.t <= GAP_DAYS * DAY;
    return !before && !after;
  });
  const gaps = shown.slice(1).map((p, i) => [shown[i].t, p.t]).filter(([a, b]) => b - a > GAP_DAYS * DAY);

  // Month ticks along the bottom (at most ~6)
  const months: number[] = [];
  const m = new Date(start); m.setDate(1); m.setHours(0, 0, 0, 0); m.setMonth(m.getMonth() + 1);
  for (; m.getTime() <= end; m.setMonth(m.getMonth() + 1)) months.push(m.getTime());
  const everyN = Math.ceil(months.length / 6);
  const monthLabel = (t: number) => new Date(t).toLocaleDateString('en-US', { month: 'short', ...(new Date(t).getMonth() === 0 ? { year: '2-digit' } : {}) });

  // Hover: snap to the nearest price point; show a call made that day too
  const h = hover != null ? shown[hover] : null;
  const hCall = h ? shownCalls.find((c) => new Date(c.t).toDateString() === new Date(h.t).toDateString()) : undefined;
  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - box.left + M.left;
    let best = 0;
    shown.forEach((p, i) => { if (Math.abs(x(p.t) - px) < Math.abs(x(shown[best].t) - px)) best = i; });
    setHover(best);
  };

  const present = (['bullish', 'bearish', 'mixed', 'neutral'] as SentimentType[]).filter((s) => shownCalls.some((c) => c.sentiment === s));
  const first = shown[0].price, last = shown[shown.length - 1].price;

  return (
    <figure className="call-chart">
      <div className="cc-head">
        <figcaption>
          <strong>Price and the AI's calls</strong>
          <span className="muted"> · {money(first)} → {money(last)} ({pct((last / first - 1) * 100)})</span>
        </figcaption>
        <div className="segmented cc-ranges" role="radiogroup" aria-label="Time range">
          {RANGES.map((r) => (
            <button key={r.id} role="radio" aria-checked={range === r.id} className={range === r.id ? 'active' : ''} onClick={() => { setRange(r.id); setHover(null); }}>{r.label}</button>
          ))}
        </div>
      </div>

      <div className="cc-plot" ref={boxRef}>
        <svg width={w} height={H} role="img"
          aria-label={`Price from ${money(first)} to ${money(last)}, with ${shownCalls.length} AI sentiment calls marked. The table below lists every sync.`}>
          {yt.map((v) => (
            <g key={v}>
              <line className="cc-grid" x1={M.left} x2={w - M.right} y1={y(v)} y2={y(v)} />
              <text className="cc-axis" x={M.left - 8} y={y(v)} dy="0.32em" textAnchor="end">{money(v, v >= 100)}</text>
            </g>
          ))}
          {months.filter((_, i) => i % everyN === 0).map((t) => (
            <text key={t} className="cc-axis" x={x(t)} y={H - 6} textAnchor="middle">{monthLabel(t)}</text>
          ))}
          {gaps.map(([a, b]) => (
            <g key={a}>
              <rect className="cc-gap" x={x(a)} y={M.top} width={x(b) - x(a)} height={H - M.top - M.bottom} />
              {x(b) - x(a) > 60 && <text className="cc-axis" x={(x(a) + x(b)) / 2} y={M.top + 12} textAnchor="middle">no price data</text>}
            </g>
          ))}
          {segments.map((s, i) => <path key={i} className="cc-line" d={s} />)}
          {lone.map((p) => <circle key={p.t} className="cc-lone" cx={x(p.t)} cy={y(p.price)} r={3} />)}
          {shownCalls.map((c) => <Marker key={c.t} s={c.sentiment} x={x(c.t)} y={y(c.price)} />)}
          {h && (
            <g pointerEvents="none">
              <line className="cc-crosshair" x1={x(h.t)} x2={x(h.t)} y1={M.top} y2={H - M.bottom} />
              <circle className="cc-dot" cx={x(h.t)} cy={y(h.price)} r={4} />
            </g>
          )}
          <rect className="cc-hit" x={M.left} y={0} width={w - M.left - M.right} height={H}
            onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {h && (
          // Keep the tooltip off the line: the half of the plot away from the point, the side away from the edge
          <div className="cc-tip" style={{
            left: x(h.t) > w - 190 ? x(h.t) - 172 : x(h.t) + 12,
            top: y(h.price) < H / 2 ? H - M.bottom - 76 : M.top,
          }}>
            <strong className="num">{money(h.price)}</strong>
            <span className="muted">{new Date(h.t).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            {hCall && (
              <span className="cc-tip-call">
                <svg width="12" height="12" aria-hidden="true"><Marker s={hCall.sentiment} x={6} y={6} r={4} /></svg>
                {SHAPE_LABEL[hCall.sentiment]} call at {money(hCall.price)}
              </span>
            )}
          </div>
        )}
      </div>

      {present.length > 0 && (
        <div className="cc-legend">
          <span><svg width="18" height="10" aria-hidden="true"><line className="cc-line" x1="1" x2="17" y1="5" y2="5" /></svg>Price</span>
          {present.map((s) => (
            <span key={s}><svg width="12" height="12" aria-hidden="true"><Marker s={s} x={6} y={6} r={4} /></svg>{SHAPE_LABEL[s]} call</span>
          ))}
        </div>
      )}
    </figure>
  );
}

export default CallChart;
