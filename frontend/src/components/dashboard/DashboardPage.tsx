import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RefreshCw, AlertTriangle, Bell, Sparkles, CalendarClock, Loader2, Plus, ArrowUp, ArrowDown, Clock } from 'lucide-react';
import { getHomeSummary, syncStaleCompanies, triggerSync, getFinnhubStatus, getScorecard, type UpcomingEarning, type FinnhubStatus } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import { triggeredAlert, livePrice } from '../../lib/prices';
import type { CompanyWithSync } from '../../types';
import { money, signedMoney, pct, direction, ago, num, shortDate, inDays } from '../../lib/format';
import SentimentBadge from '../shared/SentimentBadge';
import AddCompanyModal from '../company/AddCompanyModal';
import { isQueued, syncStepText } from '../../lib/syncSteps';
import { useTitle } from '../../lib/useTitle';
import { useSort, type SortState } from '../../lib/useSort';
import { parseTime, hoursSince } from '../../lib/format';
import { driftSince } from '../../lib/drift';
import { sentimentBias } from '../../lib/bias';
import './Dashboard.css';

const STATUS_LABEL: Record<string, string> = { public: 'Public', private: 'Private', pre_ipo: 'Pre-IPO', acquired: 'Acquired' };

function CompanyCell({ c, sentimentDot = false }: { c: CompanyWithSync; sentimentDot?: boolean }) {
  const s = c.latest_analysis?.ai_sentiment;
  return (
    <Link to={`/companies/${c.id}`} className="db-company">
      {/* On phones the Sentiment column is hidden, so a colored dot stands in for it */}
      {sentimentDot && s && <span className={`db-sent-dot show-sm sentiment-dot-${s}`} title={`AI sentiment: ${s}`} aria-label={`Sentiment ${s}`} />}
      <span className="db-company-name">{c.name}</span>
      {c.ticker && <span className="db-ticker mono">{c.ticker}</span>}
    </Link>
  );
}

function Sentiment({ c }: { c: CompanyWithSync }) {
  const s = c.latest_analysis?.ai_sentiment;
  return s ? <SentimentBadge sentiment={s} /> : <span className="muted">—</span>;
}

function Freshness({ c }: { c: CompanyWithSync }) {
  if (isQueued(c)) return <span className="db-fresh muted" title={syncStepText(c)}><Clock size={12} /> Queued</span>;
  if (c.is_syncing) return <span className="db-fresh" title={syncStepText(c)}><Loader2 size={12} className="spinning" /> Syncing</span>;
  if (c.sync_error) return <span className="db-fresh down" title={c.sync_error}><AlertTriangle size={12} /> Failed</span>;
  return <span className={`db-fresh ${c.is_stale ? 'db-stale' : 'muted'}`}>{ago(c.latest_sync?.synced_at)}</span>;
}

const SENTIMENT_RANK: Record<string, number> = { bullish: 4, mixed: 3, neutral: 2, bearish: 1 };
const time = (v: string | null | undefined) => (v ? parseTime(v).getTime() : null);

// Sort values shared by both tables
const COMMON = {
  name: (c: CompanyWithSync) => c.name.toLowerCase(),
  price: (c: CompanyWithSync) => livePrice(c)?.price,
  change: (c: CompanyWithSync) => livePrice(c)?.change,
  sentiment: (c: CompanyWithSync) => SENTIMENT_RANK[c.latest_analysis?.ai_sentiment ?? ''],
  updated: (c: CompanyWithSync) => time(c.latest_sync?.synced_at),
};
const positionValue = (c: CompanyWithSync) => {
  const p = livePrice(c)?.price;
  return p != null ? p * (c.shares_owned ?? 0) : null;
};
const PORTFOLIO_SORT = { ...COMMON, shares: (c: CompanyWithSync) => c.shares_owned, value: positionValue, weight: positionValue };

// Latest-analysis card: the newest few, plus any recent sentiment flip
const ANALYSES_SHOWN = 5;
const FLIP_DAYS = 7;
// Analyses older than this are dimmed: they describe a situation that may have moved on
const OLD_ANALYSIS_DAYS = 7;

function SortTh({ label, k, sort, onSort, numeric = false, className = '' }: {
  label: string; k: string; sort: SortState; onSort: (k: string, numeric: boolean) => void; numeric?: boolean; className?: string;
}) {
  const active = sort.key === k;
  return (
    <th className={className} aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button className={`db-sort ${active ? 'active' : ''}`} onClick={() => onSort(k, numeric)}>
        {label}
        {active && (sort.dir === 'asc' ? <ArrowUp size={11} /> : <ArrowDown size={11} />)}
      </button>
    </th>
  );
}

interface Attention {
  key: string;
  company: CompanyWithSync;
  icon: 'alert' | 'error';
  text: string;
  retry?: boolean;
}

function needsAttention(companies: CompanyWithSync[]): Attention[] {
  const items: Attention[] = [];
  for (const c of companies) {
    const alert = triggeredAlert(c);
    if (alert) {
      items.push({
        key: `${c.id}-alert`, company: c, icon: 'alert',
        text: `${money(alert.price)} is ${alert.kind} your ${money(alert.level)} alert`,
      });
    }
    if (c.is_syncing) continue;
    if (c.sync_error) items.push({ key: `${c.id}-fail`, company: c, icon: 'error', text: `Last sync failed: ${c.sync_error}`, retry: true });
    else if (!c.latest_sync) items.push({ key: `${c.id}-never`, company: c, icon: 'error', text: 'Never synced', retry: true });
    else if (c.latest_sync.error) items.push({ key: `${c.id}-ai`, company: c, icon: 'error', text: c.latest_sync.error, retry: true });
  }
  return items;
}

function DashboardPage() {
  const { companies, loaded, refresh, toast, driftPercent } = useAppData();
  const [bias, setBias] = useState<string | null>(null);
  const [earnings, setEarnings] = useState<UpcomingEarning[]>([]);
  const [queueing, setQueueing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [finnhub, setFinnhub] = useState<FinnhubStatus | null>(null);
  const [allAnalyses, setAllAnalyses] = useState(false);
  const portfolioSort = useSort('sentinel.sort.portfolio', { key: 'value', dir: 'desc' }, PORTFOLIO_SORT);
  const watchSort = useSort('sentinel.sort.watchlist', { key: 'name', dir: 'asc' }, COMMON);
  useTitle('Dashboard');

  useEffect(() => {
    getHomeSummary().then((s) => setEarnings(s.upcoming_earnings)).catch(() => {});
    getScorecard(30).then((s) => setBias(sentimentBias(s.overall))).catch(() => setBias(null));
    getFinnhubStatus().then(setFinnhub).catch(() => {});
  }, [companies.length]);

  if (!loaded) return <div className="page"><div className="muted">Loading…</div></div>;

  if (companies.length === 0) {
    return (
      <div className="page">
        <div className="db-welcome">
          <h1>Welcome to Sentinel</h1>
          <p className="muted">Track public, pre-IPO and private companies: prices, news, analyst ratings and an AI read on each.</p>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}><Plus size={16} /> Add a company</button>
        </div>
        {showAdd && <AddCompanyModal onClose={() => setShowAdd(false)} onSuccess={() => { setShowAdd(false); refresh(); }} />}
      </div>
    );
  }

  const holdings = portfolioSort.apply(companies.filter((c) => (c.shares_owned ?? 0) > 0));
  const watchlist = watchSort.apply(companies.filter((c) => !((c.shares_owned ?? 0) > 0)));
  const staleCount = companies.filter((c) => c.status === 'public' && c.ticker && c.is_stale && !c.is_syncing).length;
  const attention = needsAttention(companies);
  const hasPublic = companies.some((c) => c.status === 'public' && c.ticker);
  const marketDataProblem = hasPublic && finnhub && (!finnhub.configured || finnhub.ok === false)
    ? (finnhub.error ?? 'Finnhub is not working')
    : null;

  // Portfolio totals (positions without a price are left out of the totals)
  const rows = holdings.map((c) => {
    const live = livePrice(c);
    const price = live?.price ?? null;
    const value = price != null ? price * c.shares_owned! : null;
    const change = live?.change ?? null;
    const dayChange = value != null && change != null ? value - value / (1 + change / 100) : null;
    return { c, price, value, change, dayChange };
  });
  const total = rows.reduce((s, r) => s + (r.value ?? 0), 0);
  const totalDay = rows.reduce((s, r) => s + (r.dayChange ?? 0), 0);
  const totalDayPct = total - totalDay > 0 ? (totalDay / (total - totalDay)) * 100 : null;

  const analyses = companies
    .filter((c) => c.latest_analysis)
    .sort((a, b) => b.latest_analysis!.synced_at.localeCompare(a.latest_analysis!.synced_at));
  const flippedRecently = (c: CompanyWithSync) => {
    const la = c.latest_analysis!;
    return !!la.previous_sentiment && !!la.ai_sentiment && la.previous_sentiment !== la.ai_sentiment &&
      Date.now() - parseTime(la.synced_at).getTime() < FLIP_DAYS * 86400_000;
  };
  const shownAnalyses = allAnalyses ? analyses : analyses.filter((c, i) => i < ANALYSES_SHOWN || flippedRecently(c));

  const syncStale = async () => {
    setQueueing(true);
    try {
      const r = await syncStaleCompanies();
      toast(r.message, 'info');
      await refresh();
    } catch {
      toast('Could not start the sync', 'error');
    } finally {
      setQueueing(false);
    }
  };

  const retry = async (c: CompanyWithSync) => {
    try {
      await triggerSync(c.id);
      await refresh();
    } catch {
      toast(`Could not start a sync for ${c.name}`, 'error');
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">{companies.length} {companies.length === 1 ? 'company' : 'companies'} tracked</p>
        </div>
        <button className="btn btn-secondary" onClick={syncStale} disabled={queueing || staleCount === 0}
          title={staleCount ? 'Sync public companies whose data is older than the staleness threshold' : 'All public companies are up to date'}>
          <RefreshCw size={15} className={queueing ? 'spinning' : ''} />
          {staleCount ? `Sync ${staleCount} stale` : 'Up to date'}
        </button>
      </header>

      {(attention.length > 0 || marketDataProblem) && (
        <section className="card db-attention">
          <h2>Needs attention</h2>
          {marketDataProblem && (
            <div className="db-attention-row">
              <AlertTriangle size={15} className="down" />
              <span className="db-company-name">Market data</span>
              <span className="db-attention-text">{marketDataProblem}</span>
              <Link to="/settings" className="btn btn-ghost btn-sm">Settings</Link>
            </div>
          )}
          {attention.map((a) => (
            <div key={a.key} className="db-attention-row">
              {a.icon === 'alert' ? <Bell size={15} className="db-icon-alert" /> : <AlertTriangle size={15} className="down" />}
              <CompanyCell c={a.company} />
              <span className="db-attention-text">{a.text}</span>
              {a.retry && <button className="btn btn-ghost btn-sm" onClick={() => retry(a.company)}>Sync now</button>}
            </div>
          ))}
        </section>
      )}

      <div className="db-grid">
        <div className="db-main">
          {holdings.length > 0 && (
            <section className="card db-portfolio">
              <div className="db-portfolio-head">
                <h2>Portfolio</h2>
                <div className="db-total">
                  <span className="db-total-value num">{money(total)}</span>
                  {totalDayPct != null && (
                    <span className={`num ${direction(totalDay)}`}>{signedMoney(totalDay)} ({pct(totalDayPct)}) today</span>
                  )}
                </div>
              </div>
              <table className="db-table">
                <thead>
                  <tr>
                    <SortTh label="Company" k="name" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Shares" k="shares" numeric className="r hide-sm" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Price" k="price" numeric className="r hide-sm" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Today" k="change" numeric className="r" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Value" k="value" numeric className="r" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Weight" k="weight" numeric className="r hide-sm" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Sentiment" k="sentiment" numeric className="hide-sm" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                    <SortTh label="Updated" k="updated" numeric className="r hide-sm" sort={portfolioSort.sort} onSort={portfolioSort.toggle} />
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ c, price, value, change }) => (
                    <tr key={c.id}>
                      <td><CompanyCell c={c} sentimentDot /></td>
                      <td className="r num hide-sm">{num(c.shares_owned)}</td>
                      <td className="r num hide-sm">{money(price)}</td>
                      <td className={`r num ${direction(change)}`}>{pct(change)}</td>
                      <td className="r num">{money(value, true)}</td>
                      <td className="r num muted hide-sm">{value != null && total ? `${((value / total) * 100).toFixed(0)}%` : '—'}</td>
                      <td className="hide-sm"><Sentiment c={c} /></td>
                      <td className="r hide-sm"><Freshness c={c} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {watchlist.length > 0 && (
            <section className="card">
              <h2>{holdings.length ? 'Watchlist' : 'Companies'}</h2>
              <table className="db-table">
                <thead>
                  <tr>
                    <SortTh label="Company" k="name" sort={watchSort.sort} onSort={watchSort.toggle} />
                    <SortTh label="Price" k="price" numeric className="r" sort={watchSort.sort} onSort={watchSort.toggle} />
                    <SortTh label="Today" k="change" numeric className="r" sort={watchSort.sort} onSort={watchSort.toggle} />
                    <SortTh label="Sentiment" k="sentiment" numeric className="hide-sm" sort={watchSort.sort} onSort={watchSort.toggle} />
                    <SortTh label="Updated" k="updated" numeric className="r hide-sm" sort={watchSort.sort} onSort={watchSort.toggle} />
                  </tr>
                </thead>
                <tbody>
                  {watchlist.map((c) => {
                    const live = livePrice(c);
                    return (
                    <tr key={c.id}>
                      <td><CompanyCell c={c} sentimentDot /></td>
                      {live ? (
                        <>
                          <td className="r num">{money(live.price)}</td>
                          <td className={`r num ${direction(live.change)}`}>{pct(live.change)}</td>
                        </>
                      ) : (
                        <td className="r muted db-headline-cell" colSpan={2}>
                          {/* No price for private companies: their latest headline is the useful thing to show */}
                          {c.latest_headline ? (
                            <a href={c.latest_headline.url} target="_blank" rel="noopener noreferrer" className="db-headline"
                              title={c.latest_headline.title}>
                              {c.latest_headline.title}
                              {c.latest_headline.published_at && <span className="muted"> · {ago(c.latest_headline.published_at)}</span>}
                            </a>
                          ) : STATUS_LABEL[c.status]}
                        </td>
                      )}
                      <td className="hide-sm"><Sentiment c={c} /></td>
                      <td className="r hide-sm"><Freshness c={c} /></td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          )}
        </div>

        <aside className="db-side">
          {earnings.length > 0 && (
            <section className="card">
              <h2><CalendarClock size={15} /> Upcoming earnings</h2>
              <ul className="db-list">
                {earnings.map((e) => (
                  <li key={`${e.company_id}-${e.date}`}>
                    <Link to={`/companies/${e.company_id}`}>{e.company_name}</Link>
                    <span className="muted num">{shortDate(e.date)} · {inDays(e.date)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {analyses.length > 0 && (
            <section className="card">
              <h2><Sparkles size={15} /> Latest analysis</h2>
              <div className="db-analyses">
                {shownAnalyses.map((c) => {
                  const la = c.latest_analysis!;
                  const flipped = la.previous_sentiment && la.ai_sentiment && la.previous_sentiment !== la.ai_sentiment;
                  const old = hoursSince(la.synced_at) > OLD_ANALYSIS_DAYS * 24;
                  const drift = driftSince(la.stock_price, livePrice(c)?.price);
                  const drifted = drift != null && Math.abs(drift) >= driftPercent;
                  return (
                    <Link key={c.id} to={`/companies/${c.id}`} className={`db-analysis ${old ? 'db-analysis-old' : ''}`}>
                      <div className="db-analysis-head">
                        <span className="db-company-name">{c.name}</span>
                        {flipped && <span className="db-flip">was {la.previous_sentiment} →</span>}
                        {la.ai_sentiment && <SentimentBadge sentiment={la.ai_sentiment} />}
                        <span className={`db-analysis-time ${old ? 'db-stale' : 'muted'}`} title={old ? 'This analysis is old' : undefined}>{ago(la.synced_at)}</span>
                      </div>
                      {drifted && (
                        <div className="db-drift" title="The price has moved a lot since this analysis was written">
                          <AlertTriangle size={12} /> Price {pct(drift)} since this analysis
                        </div>
                      )}
                      <p>{la.ai_changes ?? la.ai_summary}</p>
                    </Link>
                  );
                })}
              </div>
              {bias && <p className="db-bias"><Link to="/scorecard">Scorecard</Link>: {bias}</p>}
              {(allAnalyses || shownAnalyses.length < analyses.length) && (
                <button className="btn btn-ghost btn-sm db-more" onClick={() => setAllAnalyses((v) => !v)}>
                  {allAnalyses ? 'Show fewer' : `Show all ${analyses.length}`}
                </button>
              )}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

export default DashboardPage;
