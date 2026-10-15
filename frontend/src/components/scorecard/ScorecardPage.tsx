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
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setData(null);
    setError(false);
    let current = true;
    getScorecard(horizon).then((result) => { if (current) setData(result); }).catch(() => { if (current) setError(true); });
    return () => { current = false; };
  }, [horizon, retry]);

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

      {error ? <div className="notice notice-error" role="alert">Could not load the scorecard. <button className="btn btn-ghost btn-sm" onClick={() => setRetry((n) => n + 1)}>Retry</button></div> : !data || !o ? (
        <div className="muted">Loading…</div>
      ) : o.calls === 0 ? (
        <div className="card muted">No sentiment calls on public companies yet.</div>
      ) : (
        <>
          {o.small_sample && <div className="notice notice-info">Small sample: {o.graded} graded calls. Treat these results as descriptive, especially while fewer than 30 calls have matured.</div>}
          {sentimentBias(o) && (
            <div className="notice notice-warning"><AlertTriangle size={16} /><span>{sentimentBias(o)}</span></div>
          )}
          <div className="sc-tiles">
            <div className="card sc-tile">
              <span className="sc-label">Right</span>
              <span className="sc-value">{rate(o)}</span>
              <span className="muted">{o.hits} of {o.graded} graded calls</span>
              {o.hit_rate_interval && <span className="muted">95% interval: {o.hit_rate_interval[0]}–{o.hit_rate_interval[1]}%</span>}
            </div>
            <div className="card sc-tile">
              <span className="sc-label">After bullish calls</span>
              <span className={`sc-value ${(o.avg_return.bullish ?? 0) >= 0 ? 'up' : 'down'}`}>{signed(o.avg_return.bullish)}</span>
              <span className="muted">average price change · n={o.return_samples.bullish}</span>
              <span className="muted">vs SPY: {signed(o.avg_excess_return.bullish)} excess</span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">After bearish calls</span>
              <span className={`sc-value ${(o.avg_return.bearish ?? 0) >= 0 ? 'up' : 'down'}`}>{signed(o.avg_return.bearish)}</span>
              <span className="muted">average price change · n={o.return_samples.bearish}</span>
              <span className="muted">vs SPY: {signed(o.avg_excess_return.bearish)} excess</span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">Waiting</span>
              <span className="sc-value">{o.pending}</span>
              <span className="muted">
                {horizon} days haven't passed yet
                {o.no_data > 0 && <> · {o.no_data} can't be graded (no price recorded near the date)</>}
              </span>
            </div>
            <div className="card sc-tile">
              <span className="sc-label">Right relative to SPY</span>
              <span className="sc-value">{o.benchmark_hit_rate == null ? '—' : `${o.benchmark_hit_rate}%`}</span>
              <span className="muted">{o.benchmark_graded} calls with matched benchmark prices</span>
              <span className="muted">Bullish: outperformed · Bearish: underperformed</span>
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
              <h2>By model and prompt</h2>
              <table className="data-table">
                <thead><tr><th>Model</th><th className="r">Graded</th><th className="r">Right</th></tr></thead>
                <tbody>
                  {data.by_version.map((m) => (
                    <tr key={`${m.model}-${m.prompt_version}-${m.prediction_days}`}>
                      <td><span className="mono">{m.model === 'unknown' ? 'Model not recorded' : m.model}</span><div className="muted sc-version">{m.prompt_version === 'legacy' ? 'Prompt not recorded' : m.prompt_version}<br />{m.prediction_days ? `${m.prediction_days}-day prediction` : 'Prediction horizon not recorded'}</div></td>
                      <td className="r num">{m.graded}</td>
                      <td className="r num" title={m.hit_rate_interval ? `95% interval: ${m.hit_rate_interval.join('–')}%` : undefined}>{rate(m)}{m.small_sample && <div className="muted sc-version">small sample</div>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          <section className="card">
            <h2>Recent calls</h2>
            <div className="sc-scroll"><table className="data-table">
              <thead><tr><th>Date</th><th>Company</th><th>Call</th><th className="r hide-sm">Price then</th><th className="r hide-sm">{horizon} days later</th><th className="r">Change</th><th className="r">SPY</th><th className="r">Excess</th><th>Result</th></tr></thead>
              <tbody>
                {data.recent.map((c) => (
                  <tr key={`${c.company_id}-${c.at}`}>
                    <td className="nowrap">{shortDate(c.at)}</td>
                    <td><Link to={`/companies/${c.company_id}`}>{c.name}</Link></td>
                    <td><SentimentBadge sentiment={c.sentiment as SentimentType} /></td>
                    <td className="r num hide-sm">{money(c.price)}</td>
                    <td className="r num hide-sm" title={c.later_at ? parseTime(c.later_at).toLocaleString() : undefined}>{money(c.later_price)}</td>
                    <td className={`r num ${c.return == null ? 'muted' : c.return >= 0 ? 'up' : 'down'}`}>{signed(c.return)}</td>
                    <td className="r num muted">{signed(c.benchmark_return)}</td>
                    <td className="r num" title={c.relative_hit == null ? 'No matched benchmark or non-directional call' : c.relative_hit ? 'Right relative to SPY' : 'Wrong relative to SPY'}>{signed(c.excess_return)}</td>
                    <td className={c.hit == null ? 'muted' : c.hit ? 'up' : 'down'}>{c.return == null ? (c.no_data ? 'No price data' : 'Pending') : c.hit == null ? 'Not graded' : c.hit ? 'Right' : 'Wrong'}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </section>
          <p className="muted sc-note">
            Prices come from syncs and the daily quote refresh, which records each trading day's close while Sentinel is
            running. The last call per company per New York day is retained. Evaluation uses the nearest recorded price
            within ±{data.tolerance_days} days of the selected horizon, only once that horizon has passed. This evaluation
            horizon can differ from the prediction horizon recorded beside each model/prompt version.
          </p>
          <p className="muted sc-note">
            SPY prices are collected with quote refreshes from now on. Relative results require prices at or before both
            actual evaluation endpoints, no more than three days old; missing history is left blank. Returns are price
            changes, exclude dividends and fees, and may be affected by splits. Excess is the stock return minus SPY’s return
            in percentage points. The 95% Wilson interval assumes independent calls; overlapping calls can be correlated.
          </p>
        </>
      )}
    </div>
  );
}

export default ScorecardPage;
