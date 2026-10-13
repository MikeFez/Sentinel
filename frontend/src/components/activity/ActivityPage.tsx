import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import {
  getActivityEvents, getActivitySummary,
  type ActivityEvent, type ActivityKind, type ActivitySummary,
} from '../../api/client';
import { ago, parseTime } from '../../lib/format';
import './ActivityPage.css';
import { useTitle } from '../../lib/useTitle';

const KINDS: { id: ActivityKind; label: string }[] = [
  { id: 'llm', label: 'LLM' },
  { id: 'finnhub', label: 'Finnhub' },
  { id: 'sec', label: 'SEC' },
  { id: 'sync', label: 'Syncs' },
  { id: 'job', label: 'Jobs' },
];
const RANGES = [{ hours: 24, label: 'Last 24 hours' }, { hours: 24 * 7, label: 'Last 7 days' }];
const REFRESH_MS = 5000;

const duration = (ms: number | null | undefined) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const m = Math.floor(ms / 60_000);
  return `${m}m ${Math.round((ms % 60_000) / 1000)}s`;
};
const busy = (s: number) => (s < 90 ? `${Math.round(s)} s` : s < 5400 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);
const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : String(n));

function KindTag({ kind }: { kind: ActivityKind }) {
  return <span className={`act-kind act-${kind}`}>{KINDS.find((k) => k.id === kind)?.label ?? kind}</span>;
}

function Chart({ s }: { s: ActivitySummary }) {
  const n = s.series.llm.length;
  const stacks = Array.from({ length: n }, (_, i) => KINDS.map((k) => ({ kind: k.id, v: s.series[k.id][i] })));
  const peak = Math.max(1, ...stacks.map((st) => st.reduce((a, b) => a + b.v, 0)));
  const start = parseTime(s.since).getTime();
  const label = (i: number) => {
    const d = new Date(start + i * s.bucket_seconds * 1000);
    return s.bucket_seconds === 3600
      ? d.toLocaleTimeString('en-US', { hour: 'numeric' })
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  return (
    <div className="act-chart">
      <div className="act-bars">
        {stacks.map((st, i) => {
          const total = st.reduce((a, b) => a + b.v, 0);
          return (
            <div key={i} className="act-bar" title={`${label(i)}: ${st.filter((x) => x.v).map((x) => `${x.v} ${x.kind}`).join(', ') || 'nothing'}`}>
              {st.filter((x) => x.v).map((x) => (
                <span key={x.kind} className={`act-${x.kind}`} style={{ height: `${(x.v / peak) * 100}%` }} />
              ))}
              {total === 0 && <span className="act-empty" />}
            </div>
          );
        })}
      </div>
      <div className="act-axis muted">
        <span>{label(0)}</span><span>{label(Math.floor(n / 2))}</span><span>now</span>
      </div>
      <div className="act-legend">
        {KINDS.map((k) => <span key={k.id}><i className={`act-${k.id}`} /> {k.label}</span>)}
      </div>
    </div>
  );
}

function ActivityPage() {
  useTitle('Activity');
  const [hours, setHours] = useState(24);
  const [summary, setSummary] = useState<ActivitySummary | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [kind, setKind] = useState<ActivityKind | ''>('');
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [showApi, setShowApi] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => {
      getActivitySummary(hours).then((s) => alive && setSummary(s)).catch(() => {});
      getActivityEvents(kind || null, errorsOnly).then((e) => alive && setEvents(e)).catch(() => {});
    };
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => { alive = false; clearInterval(t); };
  }, [hours, kind, errorsOnly]);

  const t = summary?.totals;
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Activity</h1>
          <p className="muted">What Sentinel has been doing: LLM, Finnhub and SEC calls, syncs and background jobs. Updates every 5 seconds.</p>
        </div>
      </header>

      <div className="tabs" role="tablist">
        {RANGES.map((r) => (
          <button key={r.hours} role="tab" aria-selected={hours === r.hours} className={`tab ${hours === r.hours ? 'active' : ''}`} onClick={() => setHours(r.hours)}>
            {r.label}
          </button>
        ))}
      </div>

      {!summary || !t ? <div className="muted">Loading…</div> : (
        <>
          <section className="card act-running">
            {summary.running.length === 0 ? (
              <span className="muted">Idle: nothing running right now.</span>
            ) : summary.running.map((r, i) => (
              <div key={i} className="act-running-row">
                <Loader2 size={14} className="spinning" />
                <KindTag kind={r.kind} />
                <span>{r.name}</span>
                {r.company_name && <span className="muted">· {r.company_name}</span>}
                <span className="muted act-running-time num">{Math.round(r.seconds)} s</span>
              </div>
            ))}
          </section>

          <div className="act-tiles">
            <div className="card act-tile">
              <span className="act-label">LLM calls</span>
              <span className="act-value">{t.llm.count}</span>
              <span className={t.llm.errors ? 'down' : 'muted'}>{t.llm.errors} failed</span>
            </div>
            <div className="card act-tile">
              <span className="act-label">LLM busy</span>
              <span className="act-value">{busy(t.llm.busy_seconds)}</span>
              <span className="muted">{compact(summary.llm_tokens.prompt)} in · {compact(summary.llm_tokens.completion)} out tokens</span>
            </div>
            <div className="card act-tile">
              <span className="act-label">Finnhub requests</span>
              <span className="act-value">{t.finnhub.count}</span>
              <span className={t.finnhub.errors ? 'down' : 'muted'}>{t.finnhub.errors} failed</span>
            </div>
            <div className="card act-tile">
              <span className="act-label">SEC requests</span>
              <span className="act-value">{t.sec.count}</span>
              <span className={t.sec.errors ? 'down' : 'muted'}>{t.sec.errors} failed</span>
            </div>
            <div className="card act-tile">
              <span className="act-label">Syncs</span>
              <span className="act-value">{t.sync.count}</span>
              <span className={t.sync.errors ? 'down' : 'muted'}>{t.sync.errors} failed · {busy(t.sync.busy_seconds)} total</span>
            </div>
          </div>

          <section className="card"><h2>Over time</h2><Chart s={summary} /></section>

          <section className="card">
            <h2>By operation</h2>
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Type</th><th>Operation</th><th className="r">Count</th><th className="r">Failed</th><th className="r hide-sm">Avg</th><th className="r hide-sm">p95</th><th className="r hide-sm">Tokens</th><th className="hide-sm">Last error</th></tr></thead>
                <tbody>
                  {summary.operations.map((o) => (
                    <tr key={`${o.kind}-${o.name}`}>
                      <td><KindTag kind={o.kind} /></td>
                      <td>{o.name}</td>
                      <td className="r num">{o.count}</td>
                      <td className={`r num ${o.errors ? 'down' : 'muted'}`}>{o.errors}</td>
                      <td className="r num hide-sm">{duration(o.avg_ms)}</td>
                      <td className="r num hide-sm">{duration(o.p95_ms)}</td>
                      <td className="r num hide-sm muted">{o.tokens ? compact(o.tokens) : '—'}</td>
                      <td className="hide-sm act-error" title={o.last_error ?? undefined}>{o.last_error ?? ''}</td>
                    </tr>
                  ))}
                  {summary.operations.length === 0 && <tr><td colSpan={8} className="muted">Nothing recorded in this period.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <div className="act-log-head">
              <h2>Event log</h2>
              <select value={kind} onChange={(e) => setKind(e.target.value as ActivityKind | '')} aria-label="Type">
                <option value="">All types</option>
                {KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
              </select>
              <label className="act-check"><input type="checkbox" checked={errorsOnly} onChange={(e) => setErrorsOnly(e.target.checked)} /> Errors only</label>
            </div>
            <div className="table-scroll">
              <table className="data-table act-log">
                <thead><tr><th>When</th><th>Type</th><th>Operation</th><th className="hide-sm">Company</th><th className="r">Took</th><th className="r hide-sm">Tokens</th><th>Result</th></tr></thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id}>
                      <td className="nowrap" title={parseTime(e.at).toLocaleString()}>{ago(e.at)}</td>
                      <td><KindTag kind={e.kind} /></td>
                      <td>{e.name}</td>
                      <td className="hide-sm">{e.company_id ? <Link to={`/companies/${e.company_id}`}>{e.company_name ?? 'deleted'}</Link> : <span className="muted">—</span>}</td>
                      <td className="r num nowrap">{duration(e.duration_ms)}</td>
                      <td className="r num hide-sm muted">{e.prompt_tokens || e.completion_tokens ? `${compact(e.prompt_tokens ?? 0)} / ${compact(e.completion_tokens ?? 0)}` : '—'}</td>
                      <td className={e.status === 'error' ? 'down act-error' : 'muted act-error'} title={e.detail ?? undefined}>
                        {e.status === 'error' ? `Failed: ${e.detail ?? ''}` : e.detail ?? 'OK'}
                      </td>
                    </tr>
                  ))}
                  {events.length === 0 && <tr><td colSpan={7} className="muted">No events.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <button className="act-api-toggle" onClick={() => setShowApi((v) => !v)} aria-expanded={showApi}>
              <h2>Sentinel API requests {showApi ? '▾' : '▸'}</h2>
              <span className="muted">since the server started</span>
            </button>
            {showApi && (
              <table className="data-table">
                <thead><tr><th>Route</th><th className="r">Requests</th><th className="r">5xx</th><th className="r">Avg</th><th className="r hide-sm">Max</th></tr></thead>
                <tbody>
                  {summary.api.map((a) => (
                    <tr key={`${a.method} ${a.route}`}>
                      <td className="mono act-route">{a.method} {a.route}</td>
                      <td className="r num">{a.count}</td>
                      <td className={`r num ${a.errors ? 'down' : 'muted'}`}>{a.errors}</td>
                      <td className="r num">{a.avg_ms} ms</td>
                      <td className="r num hide-sm">{a.max_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <p className="muted act-note">
            Events are kept for 14 days. Prometheus metrics for the same data are at <code>/metrics</code>, if you want them in Grafana.
          </p>
        </>
      )}
    </div>
  );
}

export default ActivityPage;
