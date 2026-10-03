import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { RefreshCw, Pencil, MoreHorizontal, Trash2, Bell, AlertTriangle, Loader2, ExternalLink } from 'lucide-react';
import { deleteCompany, triggerSync, getCompanySyncs } from '../../api/client';
import { useAppData, triggeredAlert, livePrice } from '../../state/AppData';
import type { Sync } from '../../types';
import { money, pct, direction, ago, parseTime, hoursSince } from '../../lib/format';
import StockDataPanel from './StockDataPanel';
import AiAnalysisPanel from './AiAnalysisPanel';
import NewsFeed from './NewsFeed';
import AnalystRatings from './AnalystRatings';
import EarningsCalendar from './EarningsCalendar';
import InsiderTransactions from './InsiderTransactions';
import SentimentBadge from '../shared/SentimentBadge';
import TagChip from '../shared/TagChip';
import SentimentSparkline from './SentimentSparkline';
import PriceChart from './PriceChart';
import AddCompanyModal from './AddCompanyModal';
import './CompanyDetail.css';

type Tab = 'overview' | 'news' | 'insiders' | 'history';
const STATUS_LABEL: Record<string, string> = { public: 'Public', private: 'Private', pre_ipo: 'Pre-IPO', acquired: 'Acquired' };

function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { companies, loaded, refresh, toast, stalenessHours } = useAppData();
  const company = companies.find((c) => c.id === id);
  const [syncs, setSyncs] = useState<Sync[]>([]);
  const [tab, setTab] = useState<Tab>('overview');
  const [showEdit, setShowEdit] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const loadSyncs = useCallback(async () => {
    if (!id) return;
    try {
      setSyncs(await getCompanySyncs(id));
    } catch (err) {
      console.error('Failed to load syncs:', err);
    }
  }, [id]);

  useEffect(() => {
    setTab('overview');
    setSyncs([]);
    loadSyncs();
  }, [id, loadSyncs]);

  // Reload the detail once a running sync finishes (the shared company list is polled while syncing)
  const syncing = company?.is_syncing ?? false;
  const wasSyncing = useRef(syncing);
  useEffect(() => {
    if (wasSyncing.current && !syncing) loadSyncs();
    wasSyncing.current = syncing;
  }, [syncing, loadSyncs]);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => { if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [menuOpen]);

  if (!loaded) return <div className="page"><div className="muted">Loading…</div></div>;
  if (!company) return <div className="page"><div className="muted">This company doesn't exist (it may have been deleted).</div></div>;

  const completed = syncs.filter((s) => s.status === 'completed');
  const latest = completed[0];
  // The newest analysis may be older than the newest data if the last analysis run failed
  const analysisSync = completed.find((s) => s.ai_summary);
  const alert = triggeredAlert(company);
  const live = livePrice(company);
  const stale = !latest || hoursSince(latest.synced_at) > stalenessHours;
  const newsCount = latest?.raw_news?.length ?? 0;
  const insiderCount = latest?.insider_transactions?.length ?? 0;

  const sync = async () => {
    try {
      await triggerSync(company.id);
      await refresh();
    } catch {
      toast(`Could not start a sync for ${company.name}`, 'error');
    }
  };

  const remove = async () => {
    setMenuOpen(false);
    if (!confirm(`Delete ${company.name} and all of its sync history? This can't be undone.`)) return;
    try {
      await deleteCompany(company.id);
      await refresh();
      toast(`Deleted ${company.name}`, 'info');
      navigate('/');
    } catch {
      toast(`Could not delete ${company.name}`, 'error');
    }
  };

  const tabs: { id: Tab; label: string; count?: number; show: boolean }[] = [
    { id: 'overview', label: 'Overview', show: true },
    { id: 'news', label: 'News', count: newsCount, show: newsCount > 0 },
    { id: 'insiders', label: 'Insider trades', count: insiderCount, show: insiderCount > 0 },
    { id: 'history', label: 'History', count: syncs.length, show: syncs.length > 0 },
  ];

  return (
    <>
      <div className="page company-page">
        <header className="cd-head">
          <div className="cd-title">
            <div className="cd-title-row">
              <h1>{company.name}</h1>
              {company.ticker && <span className="cd-ticker mono">{company.ticker}</span>}
            </div>
            <div className="cd-meta">
              <span className={`status-badge status-${company.status}`}>{STATUS_LABEL[company.status]}</span>
              {company.industry && <span className="cd-chip">{company.industry}</span>}
              {company.tags.map((t) => <TagChip key={t.id} tag={t} />)}
              {company.website && (
                <a href={company.website} target="_blank" rel="noopener noreferrer" className="cd-link">
                  {company.website.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')} <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>

          <div className="cd-actions">
            <button className="btn btn-primary" onClick={sync} disabled={syncing}>
              {syncing ? <Loader2 size={15} className="spinning" /> : <RefreshCw size={15} />}
              {syncing ? 'Syncing…' : 'Sync now'}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowEdit(true)}><Pencil size={15} /> Edit</button>
            <div className="cd-menu" ref={menuRef}>
              <button className="btn btn-secondary cd-menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="More actions" aria-expanded={menuOpen}>
                <MoreHorizontal size={16} />
              </button>
              {menuOpen && (
                <div className="cd-menu-pop" role="menu">
                  <button role="menuitem" className="cd-menu-danger" onClick={remove}><Trash2 size={14} /> Delete company</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="cd-summary">
          {live && (
            <div className="cd-price" title={`Price as of ${parseTime(live.at).toLocaleString()}`}>
              <span className="cd-price-value num">{money(live.price)}</span>
              <span className={`num ${direction(live.change)}`}>{pct(live.change)} today</span>
              <span className="muted cd-price-at">{ago(live.at)}</span>
            </div>
          )}
          {analysisSync?.ai_sentiment && (
            <div className="cd-sentiment">
              <SentimentBadge sentiment={analysisSync.ai_sentiment} />
              <SentimentSparkline syncs={syncs} />
            </div>
          )}
          <div className={`cd-updated ${stale ? 'cd-stale' : 'muted'}`} title={latest ? parseTime(latest.synced_at).toLocaleString() : undefined}>
            {latest ? `News & analysis updated ${ago(latest.synced_at)}` : 'Not synced yet'}
          </div>
        </div>

        {syncing && (
          <div className="notice notice-info"><Loader2 size={16} className="spinning" />
            <span>Syncing: fetching {company.status === 'public' ? 'prices, analyst ratings and news' : 'news'}, then running the AI analysis. This usually takes under a minute.</span>
          </div>
        )}
        {!syncing && company.sync_error && (
          <div className="notice notice-error"><AlertTriangle size={16} />
            <span>The last sync failed: {company.sync_error}{latest ? ` Showing data from ${ago(latest.synced_at)}.` : ''}</span>
            <button className="btn btn-ghost btn-sm" onClick={sync}>Retry</button>
          </div>
        )}
        {alert && (
          <div className="notice notice-warning"><Bell size={16} />
            <span>Price alert: {money(alert.price)} is {alert.kind} your {money(alert.level)} alert.</span>
          </div>
        )}

        {tabs.filter((t) => t.show).length > 1 && (
          <div className="tabs" role="tablist">
            {tabs.filter((t) => t.show).map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id} className={`tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
                {t.label}{t.count != null && <span className="tab-count">{t.count}</span>}
              </button>
            ))}
          </div>
        )}

        {tab === 'overview' && (
          <div className="cd-overview">
            {!latest && !syncing && (
              <div className="card cd-empty">
                <p>No data yet. Sync to fetch {company.status === 'public' ? 'prices, news, analyst ratings' : 'news'} and an AI analysis.</p>
                <button className="btn btn-primary" onClick={sync}><RefreshCw size={15} /> Sync now</button>
              </div>
            )}
            {latest?.error && (
              <div className="notice notice-warning"><AlertTriangle size={16} />
                <span>
                  {latest.error}.{' '}
                  {analysisSync ? `The analysis below is from ${ago(analysisSync.synced_at)}.` : ''}
                </span>
              </div>
            )}
            {analysisSync && <AiAnalysisPanel sync={analysisSync} />}
            {company.description && <div className="card cd-description">{company.description}</div>}
            {company.status === 'public' && latest && <StockDataPanel sync={latest} ticker={company.ticker} />}
            <div className="cd-two">
              {latest?.analyst_ratings && <AnalystRatings ratings={latest.analyst_ratings} />}
              {latest?.earnings_dates && latest.earnings_dates.length > 0 && <EarningsCalendar earnings={latest.earnings_dates} />}
            </div>
          </div>
        )}

        {tab === 'news' && latest?.raw_news && <NewsFeed articles={latest.raw_news} />}
        {tab === 'insiders' && latest?.insider_transactions && <InsiderTransactions transactions={latest.insider_transactions} />}

        {tab === 'history' && (
          <div className="card">
            {company.status === 'public' && <PriceChart syncs={completed} />}
            <table className="cd-history">
              <thead><tr><th>When</th><th className="r">Price</th><th className="r hide-sm">Change</th><th>Sentiment</th><th className="hide-sm">Result</th></tr></thead>
              <tbody>
                {syncs.map((s) => (
                  <tr key={s.id}>
                    <td title={parseTime(s.synced_at).toLocaleString()}>{parseTime(s.synced_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}</td>
                    <td className="r num">{money(s.stock_price)}</td>
                    <td className={`r num hide-sm ${direction(s.price_change)}`}>{pct(s.price_change)}</td>
                    <td>{s.ai_sentiment ? <SentimentBadge sentiment={s.ai_sentiment} /> : <span className="muted">—</span>}</td>
                    <td className={`hide-sm ${s.status === 'failed' ? 'down' : s.error ? 'cd-warn' : 'muted'}`}>
                      {s.status === 'syncing' ? 'Syncing…' : s.status === 'failed' ? `Failed: ${s.error ?? 'unknown error'}` : s.error ? 'No analysis' : 'OK'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showEdit && (
        <AddCompanyModal company={company} onClose={() => setShowEdit(false)} onSuccess={() => { setShowEdit(false); refresh(); }} />
      )}
    </>
  );
}

export default CompanyDetail;
