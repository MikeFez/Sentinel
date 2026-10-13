import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getScorecard, type Scorecard, type ScoreSummary } from '../../api/client';
import { money, parseTime, shortDate } from '../../lib/format';
import SentimentBadge from '../shared/SentimentBadge';
import type { SentimentType } from '../../types';
import './ScorecardPage.css';
import { useTitle } from '../../lib/useTitle';
import { sentimentBias } from '../../lib/bias';
import { AlertTriangle } from 'lucide-react';

const HORIZONS = [7, 30, 90];

const signed = (n: number | null) => (n == null ? '—' : `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(1)}%`);
const rate = (s: ScoreSummary) => (s.hit_rate == null ? '—' : `${Math.round(s.hit_rate)}%`);

function ScorecardPage() {
  useTitle('AI scorecard');
  const [horizon, setHorizon] = useState(30);
  const [data, setData] = useState<Scorecard | null>(null);

  useEffect(() => {
    setData(null);
    getScorecard(horizon).then(setData).catch(() => setData(null));
  }, [horizon]);

  const o = data?.overall;
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>AI scorecard</h1>
          <p className="muted">
            How the AI's sentiment calls played out. A bullish call is right if the price was higher {horizon} days later,
            a bearish call if it was lower. Neutral and mixed calls aren't graded.
          </p>
        </div>
      </header>

      <div className="tabs" role="tablist">
        {HORIZONS.map((h) => (
          <button key={h} role="tab" aria-selected={horizon === h} className={`tab ${horizon === h ? 'active' : ''}`} onClick={() => setHorizon(h)}>
            After {h} days
          </button>
        ))}
      </div>

      {!data || !o ? (
        <div className="muted">Loading…</div>
      ) : o.calls === 0 ? (
        <div className="card muted">No sentiment calls on public companies yet.</div>
      ) : (
        <>
          {sentimentBias(o) && (
            <div className="notice notice-warning"><AlertTriangle size={16} /><span>{sentimentBias(o)}</span></div>
          )}
          <div className="sc-tiles">
            <div className="card sc-tile">
              <span className="sc-label">Right</span>
              <span className="sc-value">{rate(o)}</span>
              <span className="muted">{o.hits} of {o.graded} graded calls</span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">After bullish calls</span>
              <span className={`sc-value ${(o.avg_return.bullish ?? 0) >= 0 ? 'up' : 'down'}`}>{signed(o.avg_return.bullish)}</span>
              <span className="muted">average price change</span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">After bearish calls</span>
              <span className={`sc-value ${(o.avg_return.bearish ?? 0) >= 0 ? 'up' : 'down'}`}>{signed(o.avg_return.bearish)}</span>
              <span className="muted">average price change</span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">Waiting</span>
              <span className="sc-value">{o.pending}</span>
              <span className="muted">
                {horizon} days haven't passed yet
                {o.no_data > 0 && <> · {o.no_data} can't be graded (no price recorded near the date)</>}
              </span>
            </div>
          </div>

          <div className="sc-grid">
            <section className="card">
              <h2>By company</h2>
              <table className="data-table">
                <thead><tr><th>Company</th><th className="r">Graded</th><th className="r">Right</th><th className="r hide-sm">After bullish</th><th className="r hide-sm">After bearish</th></tr></thead>
                <tbody>
                  {data.by_company.map((c) => (
                    <tr key={c.company_id}>
                      <td><Link to={`/companies/${c.company_id}`}>{c.name}</Link></td>
                      <td className="r num">{c.graded}</td>
                      <td className="r num">{rate(c)}</td>
                      <td className="r num hide-sm">{signed(c.avg_return.bullish)}</td>
                      <td className="r num hide-sm">{signed(c.avg_return.bearish)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="card">
              <h2>By model</h2>
              <table className="data-table">
                <thead><tr><th>Model</th><th className="r">Graded</th><th className="r">Right</th></tr></thead>
                <tbody>
                  {data.by_model.map((m) => (
                    <tr key={m.model}>
                      <td className="mono">{m.model === 'unknown' ? <span className="muted">before tracking</span> : m.model}</td>
                      <td className="r num">{m.graded}</td>
                      <td className="r num">{rate(m)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          <section className="card">
            <h2>Recent calls</h2>
            <table className="data-table">
              <thead><tr><th>Date</th><th>Company</th><th>Call</th><th className="r hide-sm">Price then</th><th className="r hide-sm">{horizon} days later</th><th className="r">Change</th><th>Result</th></tr></thead>
              <tbody>
                {data.recent.map((c) => (
                  <tr key={`${c.company_id}-${c.at}`}>
                    <td className="nowrap">{shortDate(c.at)}</td>
                    <td><Link to={`/companies/${c.company_id}`}>{c.name}</Link></td>
                    <td><SentimentBadge sentiment={c.sentiment as SentimentType} /></td>
                    <td className="r num hide-sm">{money(c.price)}</td>
                    <td className="r num hide-sm" title={c.later_at ? parseTime(c.later_at).toLocaleString() : undefined}>{money(c.later_price)}</td>
                    <td className={`r num ${c.return == null ? 'muted' : c.return >= 0 ? 'up' : 'down'}`}>{signed(c.return)}</td>
                    <td className={c.hit == null ? 'muted' : c.hit ? 'up' : 'down'}>{c.return == null ? (c.no_data ? 'No price data' : 'Pending') : c.hit == null ? 'Not graded' : c.hit ? 'Right' : 'Wrong'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <p className="muted sc-note">
            Prices come from syncs and the daily quote refresh, which records each trading day's close while Sentinel is
            running. Calls whose date fell in a stretch when it wasn't running can't be graded. Price moves include the whole
            market's moves; this isn't benchmarked.
          </p>
        </>
      )}
    </div>
  );
}

export default ScorecardPage;
