import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Check, ChevronDown, ChevronUp, Loader, Sparkles } from 'lucide-react';
import { startDiscover, getDiscoverSession, analyzeDiscoverCompany, createCompany } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import type { DiscoverSession, DiscoverCompany } from '../../api/client';
import type { SentimentType } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import './DiscoverPage.css';

const STAGE_LABELS: Record<string, string> = {
  starting: 'Initializing…',
  expanding: 'Asking AI to expand keywords…',
  searching: 'Searching SEC EDGAR filings…',
  validating: 'Validating tickers with Finnhub…',
  complete: 'Done',
  failed: 'Failed',
};

function formatMarketCap(val: string | null) {
  if (!val) return '—';
  return val;
}

function formatPrice(val: number | null) {
  if (val == null) return '—';
  return `$${val.toFixed(2)}`;
}

function formatChange(val: number | null) {
  if (val == null) return null;
  const cls = val >= 0 ? 'up' : 'down';
  const sign = val >= 0 ? '+' : '';
  return <span className={`discover-change ${cls}`}>{sign}{val.toFixed(2)}%</span>;
}

interface CompanyRowProps {
  company: DiscoverCompany;
  sessionId: string;
  onSessionUpdate: () => void;
  onWatch: (c: DiscoverCompany) => void;
}

function CompanyRow({ company, sessionId, onSessionUpdate, onWatch }: CompanyRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [watching, setWatching] = useState(false);
  const [watched, setWatched] = useState(false);

  const isAnalyzing = company.status === 'analyzing';
  const hasResult = company.sentiment != null || company.summary != null;

  const handleAnalyze = async () => {
    await analyzeDiscoverCompany(sessionId, company.ticker);
    onSessionUpdate(); // trigger parent to start polling
  };

  const handleWatch = async () => {
    setWatching(true);
    try {
      await onWatch(company);
      setWatched(true);
    } finally {
      setWatching(false);
    }
  };

  return (
    <>
      <tr className={`discover-row ${expanded ? 'expanded' : ''}`}>
        <td className="discover-cell-company">
          <div className="discover-company-name">{company.name}</div>
          <div className="discover-company-ticker">{company.ticker}</div>
        </td>
        <td className="discover-cell-num">
          {formatPrice(company.stock_price)}
          <div>{formatChange(company.price_change)}</div>
        </td>
        <td className="discover-cell-num">{formatMarketCap(company.market_cap)}</td>
        <td className="discover-cell-num">
          <span className="discover-hits" title="Keyword matches in SEC 10-K filings">
            {company.edgar_hits}
          </span>
        </td>
        <td className="discover-cell-sentiment">
          {isAnalyzing ? (
            <span className="discover-analyzing-label">
              <Loader size={13} className="discover-row-spinner" /> Analyzing…
            </span>
          ) : hasResult && company.sentiment ? (
            <SentimentBadge sentiment={company.sentiment as SentimentType} />
          ) : (
            <span className="discover-na">—</span>
          )}
        </td>
        <td className="discover-cell-actions">
          <div className="discover-row-actions">
            {hasResult && company.summary && (
              <button
                className="discover-expand-btn"
                onClick={() => setExpanded((v) => !v)}
                title={expanded ? 'Collapse summary' : 'Show AI summary'}
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            )}
            {!hasResult && !isAnalyzing && (
              <button
                className="discover-analyze-btn"
                onClick={handleAnalyze}
                title="Run sentiment analysis"
              >
                <Sparkles size={13} />
                Analyze
              </button>
            )}
            <button
              className={`discover-watch-btn ${watched ? 'watched' : ''}`}
              onClick={handleWatch}
              disabled={watching || watched}
              title={watched ? 'Added to watchlist' : 'Add to watchlist'}
            >
              {watched ? <Check size={13} /> : watching ? <Loader size={13} className="discover-row-spinner" /> : <Plus size={13} />}
              {watched ? 'Added' : 'Watch'}
            </button>
          </div>
        </td>
      </tr>
      {expanded && company.summary && (
        <tr className="discover-summary-row">
          <td colSpan={6}>
            <div className="discover-summary-text">
              {company.summary.split('\n').filter(Boolean).map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

type SortKey = 'edgar_hits' | 'sentiment' | 'price_change' | 'stock_price';

const SENTIMENT_ORDER: Record<string, number> = {
  bullish: 0,
  mixed: 1,
  neutral: 2,
  bearish: 3,
};

function sortCompanies(companies: DiscoverCompany[], key: SortKey, dir: 'asc' | 'desc') {
  return [...companies].sort((a, b) => {
    let cmp = 0;
    if (key === 'sentiment') {
      cmp = (SENTIMENT_ORDER[a.sentiment ?? ''] ?? 4) - (SENTIMENT_ORDER[b.sentiment ?? ''] ?? 4);
    } else if (key === 'edgar_hits') {
      cmp = (a.edgar_hits ?? 0) - (b.edgar_hits ?? 0);
    } else if (key === 'price_change') {
      cmp = (a.price_change ?? -Infinity) - (b.price_change ?? -Infinity);
    } else if (key === 'stock_price') {
      cmp = (a.stock_price ?? 0) - (b.stock_price ?? 0);
    }
    return dir === 'asc' ? cmp : -cmp;
  });
}

function DiscoverPage() {
  const [theme, setTheme] = useState('');
  const [session, setSession] = useState<DiscoverSession | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [error, setError] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('edgar_hits');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const navigate = useNavigate();
  const { companies: tracked, refresh, toast } = useAppData();

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = useCallback((sessionId: string) => {
    if (pollRef.current) return; // already polling
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getDiscoverSession(sessionId);
        setSession(updated);

        const discoveryDone = updated.status === 'complete' || updated.status === 'failed';
        const anyAnalyzing = updated.companies.some((c) => c.status === 'analyzing');

        if (discoveryDone && !anyAnalyzing) {
          stopPolling();
          setDiscovering(false);
          setAnalyzingAll(false);
        }
      } catch {
        stopPolling();
        setDiscovering(false);
      }
    }, 2000);
  }, []);

  useEffect(() => () => stopPolling(), []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!theme.trim()) return;

    stopPolling();
    setDiscovering(true);
    setError('');
    setSession(null);
    setAnalyzingAll(false);
    sessionIdRef.current = null;

    try {
      const initial = await startDiscover(theme.trim());
      sessionIdRef.current = initial.session_id;
      setSession(initial);
      startPolling(initial.session_id);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Discovery failed. Check the LLM endpoint is reachable.');
      setDiscovering(false);
    }
  };

  // Called by a row when the user clicks Analyze — resumes polling to pick up the result
  const handleAnalyzeTrigger = () => {
    if (sessionIdRef.current && !pollRef.current) {
      startPolling(sessionIdRef.current);
    }
  };

  const handleAnalyzeAll = async () => {
    if (!session || !sessionIdRef.current) return;
    setAnalyzingAll(true);
    const pending = session.companies.filter(
      (c) => c.status === 'pending' && c.sentiment == null
    );
    for (const company of pending) {
      await analyzeDiscoverCompany(session.session_id, company.ticker);
    }
    if (sessionIdRef.current && !pollRef.current) {
      startPolling(sessionIdRef.current);
    }
  };

  const handleWatch = async (company: DiscoverCompany) => {
    const existing = tracked.find((c) => c.ticker?.toUpperCase() === company.ticker.toUpperCase());
    if (existing) {
      navigate(`/companies/${existing.id}`);
      return;
    }
    try {
      const created = await createCompany({ name: company.name, ticker: company.ticker, status: 'public' });
      await refresh();
      toast(`Now tracking ${created.name}`, 'success');
      navigate(`/companies/${created.id}`);
    } catch {
      toast(`Could not add ${company.name}`, 'error');
    }
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span className="discover-sort-icon">⇅</span>;
    return <span className="discover-sort-icon active">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const discoveryRunning = discovering && session?.status !== 'complete' && session?.status !== 'failed';
  const showResults = session && (session.status === 'complete' || session.companies.length > 0);
  const companies = session ? sortCompanies(session.companies, sortKey, sortDir) : [];
  const noResults = session?.status === 'complete' && companies.length === 0;
  const unanalyzedCount = session?.companies.filter(
    (c) => c.status === 'pending' && c.sentiment == null
  ).length ?? 0;

  return (
    <div className="discover-page">
      <form className="discover-form" onSubmit={handleSubmit}>
        <div className="discover-input-row">
          <input
            type="text"
            className="discover-input"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            placeholder="e.g. Water Desalination, Nuclear Fusion, AI Infrastructure…"
            disabled={discoveryRunning}
            autoFocus
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!theme.trim() || discoveryRunning}
          >
            <Search size={16} className={discoveryRunning ? 'spinning' : ''} />
            {discoveryRunning ? 'Discovering…' : 'Discover'}
          </button>
        </div>
        <p className="discover-hint">
          Sentinel searches SEC 10-K filings for matching companies and validates each ticker.
          Sentiment analysis runs only when you request it.
        </p>
      </form>

      {error && <div className="discover-error">{error}</div>}

      {/* Discovery progress (only while pipeline is running) */}
      {discoveryRunning && session && (
        <div className="discover-progress-panel">
          <div className="discover-stage-row">
            <Loader size={16} className="spinning" />
            <span className="discover-stage-label">{STAGE_LABELS[session.status] ?? session.status}</span>
          </div>

          {session.keywords.length > 0 && (
            <div className="discover-keywords">
              <span className="discover-keywords-label">Keywords:</span>
              {session.keywords.map((kw) => (
                <span key={kw} className="discover-keyword-chip">{kw}</span>
              ))}
            </div>
          )}

          {session.rationale && (
            <p className="discover-rationale">{session.rationale}</p>
          )}

          {session.companies.length > 0 && (
            <div className="discover-found-chips">
              <span className="discover-keywords-label">Found:</span>
              {session.companies.map((c) => (
                <span key={c.ticker} className="discover-found-chip discover-found-chip--pending">
                  {c.ticker}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results table — visible as soon as any companies exist */}
      {showResults && companies.length > 0 && (
        <div className="discover-results">
          <div className="discover-results-header">
            <div className="discover-results-title-row">
              <div>
                <h2>
                  {companies.length} {companies.length === 1 ? 'company' : 'companies'} in "{session!.theme}"
                </h2>
                {session!.rationale && <p className="discover-rationale">{session!.rationale}</p>}
              </div>
              {session!.status === 'complete' && unanalyzedCount > 0 && (
                <button
                  className="btn btn-secondary discover-analyze-all-btn"
                  onClick={handleAnalyzeAll}
                  disabled={analyzingAll}
                >
                  <Sparkles size={14} className={analyzingAll ? 'spinning' : ''} />
                  {analyzingAll ? 'Analyzing…' : `Analyze All (${unanalyzedCount})`}
                </button>
              )}
            </div>
          </div>

          <div className="discover-table-wrap">
            <table className="discover-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th className="discover-th-sortable" onClick={() => toggleSort('stock_price')}>
                    Price <SortIcon col="stock_price" />
                  </th>
                  <th>Mkt Cap</th>
                  <th className="discover-th-sortable" onClick={() => toggleSort('edgar_hits')}>
                    Relevance <SortIcon col="edgar_hits" />
                  </th>
                  <th className="discover-th-sortable" onClick={() => toggleSort('sentiment')}>
                    Sentiment <SortIcon col="sentiment" />
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => (
                  <CompanyRow
                    key={company.ticker}
                    company={company}
                    sessionId={session!.session_id}
                    onSessionUpdate={handleAnalyzeTrigger}
                    onWatch={handleWatch}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {noResults && (
        <div className="discover-empty">
          <p>No publicly traded companies found for "{session?.theme}".</p>
          <p className="discover-empty-hint">
            Try a more specific technical term, or check that the LLM returned useful keywords above.
          </p>
        </div>
      )}

      {session?.status === 'failed' && (
        <div className="discover-error">{session.error || 'Discovery failed. Check the LLM endpoint is reachable.'}</div>
      )}
    </div>
  );
}

export default DiscoverPage;
