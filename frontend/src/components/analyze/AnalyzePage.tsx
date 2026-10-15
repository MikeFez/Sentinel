import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, ArrowRight } from 'lucide-react';
import { runAnalysis, createCompany, errorDetail, getResearch, type AnalyzeRequest } from '../../api/client';
import ResearchHistory from '../research/ResearchHistory';
import { ago } from '../../lib/format';
import { useAppData } from '../../state/useAppData';
import type { AnalyzeResult } from '../../api/client';
import type { SentimentType } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import { EvidenceLinks, EvidenceSources } from '../shared/AnalysisEvidence';
import './AnalyzePage.css';
import '../company/AiAnalysisPanel.css';

function AnalyzePage() {
  const [ticker, setTicker] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [notes, setNotes] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [error, setError] = useState('');
  const [analyzed, setAnalyzed] = useState<{ ticker: string; name: string } | null>(null);
  // The saved copy on screen, and when it was made if it was reopened from history
  const [savedId, setSavedId] = useState<string | null>(null);
  const [reopenedAt, setReopenedAt] = useState<string | null>(null);
  const [historyKey, setHistoryKey] = useState(0);
  const { companies, refresh, toast } = useAppData();
  const navigate = useNavigate();
  const tracked = analyzed?.ticker ? companies.find((c) => c.ticker?.toUpperCase() === analyzed.ticker) : undefined;

  const track = async () => {
    if (!analyzed?.ticker) return;
    try {
      const created = await createCompany({ name: analyzed.name || analyzed.ticker, ticker: analyzed.ticker, status: 'public' });
      await refresh();
      toast(`Now tracking ${created.name}`, 'success');
      navigate(`/companies/${created.id}`);
    } catch {
      toast('Could not add the company', 'error');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim() && !companyName.trim() && !notes.trim()) return;

    setRunning(true);
    setResult(null);
    setError('');
    setShowPrompt(false);

    try {
      const data = await runAnalysis({
        ticker: ticker.trim().toUpperCase() || undefined,
        company_name: companyName.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      setResult(data);
      setAnalyzed({ ticker: ticker.trim().toUpperCase(), name: companyName.trim() });
      setSavedId(data.id ?? null);
      setReopenedAt(null);
      setHistoryKey((k) => k + 1);
    } catch (err) {
      setError(errorDetail(err, 'Analysis failed. Check the LLM endpoint is reachable.'));
    } finally {
      setRunning(false);
    }
  };

  const reopen = async (id: string) => {
    try {
      const saved = await getResearch<{ request: AnalyzeRequest; result: AnalyzeResult }>(id);
      const { request, result: r } = saved.data;
      setTicker(request.ticker ?? '');
      setCompanyName(request.company_name ?? '');
      setNotes(request.notes ?? '');
      setAnalyzed({ ticker: (request.ticker ?? '').toUpperCase(), name: request.company_name ?? '' });
      setResult(r);
      setSavedId(id);
      setReopenedAt(saved.created_at);
      setError('');
      setShowPrompt(false);
    } catch {
      toast('Could not open that analysis', 'error');
    }
  };

  const stockData = result?.stock_data as Record<string, unknown> | null;
  const evidenceScope = savedId ?? 'research-analysis';
  const citations = (section: string, index: number) => <EvidenceLinks evidence={result?.evidence} section={section} index={index} scope={evidenceScope} />;

  return (
    <div className="analyze-page">
      <div className="analyze-layout">
        <div className="analyze-form-card">
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="analyze-ticker">Ticker Symbol</label>
                <input
                  id="analyze-ticker"
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="e.g. AAPL"
                  autoFocus
                />
                <small className="form-hint">
                  If provided, live price, news, and analyst data will be fetched
                </small>
              </div>
              <div className="form-group">
                <label htmlFor="analyze-name">Company / Topic Name</label>
                <input
                  id="analyze-name"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Apple Inc."
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="analyze-notes">Additional context / notes</label>
              <textarea
                id="analyze-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                placeholder="Paste news, a thesis, or any background context you want the AI to consider..."
              />
            </div>

            {error && <div className="analyze-error">{error}</div>}

            <button
              type="submit"
              className="btn btn-primary analyze-submit"
              disabled={running || (!ticker.trim() && !companyName.trim() && !notes.trim())}
            >
              <Search size={16} className={running ? 'spinning' : ''} />
              {running ? 'Analyzing…' : 'Run Analysis'}
            </button>
          </form>
        </div>

        {running && (
          <div className="analyze-running">
            <div className="analyze-spinner" />
            <p>Fetching data and running AI analysis…</p>
          </div>
        )}

        {result && !running && (
          <div className="analyze-result">
            <div className="analyze-result-header">
              <h2>Analysis Result</h2>
              {reopenedAt && <span className="muted analyze-saved-at">from {ago(reopenedAt)} · prices as of then</span>}
              {result.sentiment && (
                <SentimentBadge sentiment={result.sentiment as SentimentType} />
              )}
              {analyzed?.ticker && (tracked ? (
                <button className="btn btn-secondary btn-sm analyze-track" onClick={() => navigate(`/companies/${tracked.id}`)}>
                  Open {tracked.name} <ArrowRight size={14} />
                </button>
              ) : (
                <button className="btn btn-primary btn-sm analyze-track" onClick={track}>
                  <Plus size={14} /> Track {analyzed.ticker}
                </button>
              ))}
            </div>

            {result.prediction_days && <p className="muted">{result.prediction_days}-day outlook · {result.model} · {result.prompt_version}</p>}
            {stockData && (
              <div className="analyze-stock-grid">
                {stockData.stock_price != null && (
                  <div className="analyze-stock-item">
                    <div className="analyze-stock-label">Price</div>
                    <div className="analyze-stock-value">${(stockData.stock_price as number).toFixed(2)}</div>
                  </div>
                )}
                {stockData.price_change != null && (
                  <div className="analyze-stock-item">
                    <div className="analyze-stock-label">Today</div>
                    <div className={`analyze-stock-value ${(stockData.price_change as number) >= 0 ? 'up' : 'down'}`}>
                      {(stockData.price_change as number) >= 0 ? '+' : ''}{(stockData.price_change as number).toFixed(2)}%
                    </div>
                  </div>
                )}
                {stockData.market_cap != null && (
                  <div className="analyze-stock-item">
                    <div className="analyze-stock-label">Mkt Cap</div>
                    <div className="analyze-stock-value">{stockData.market_cap as string}</div>
                  </div>
                )}
                {stockData.fifty_two_wk_hi != null && (
                  <div className="analyze-stock-item">
                    <div className="analyze-stock-label">52W High</div>
                    <div className="analyze-stock-value">${(stockData.fifty_two_wk_hi as number).toFixed(2)}</div>
                  </div>
                )}
                {stockData.fifty_two_wk_lo != null && (
                  <div className="analyze-stock-item">
                    <div className="analyze-stock-label">52W Low</div>
                    <div className="analyze-stock-value">${(stockData.fifty_two_wk_lo as number).toFixed(2)}</div>
                  </div>
                )}
              </div>
            )}

            {result.summary && (
              <div className="analyze-summary">
                {result.summary.split('\n').filter((line) => line.trim()).map((line, i) => (
                  <p key={i}>{line}{citations('summary', i)}</p>
                ))}
              </div>
            )}

            {(result.key_points.length > 0 || result.risks.length > 0) && (
              <div className="ai-lists">
                {result.key_points.length > 0 && (
                  <div><h3>Key points</h3><ul>{result.key_points.map((k, i) => <li key={i}>{k}{citations('key_points', i)}</li>)}</ul></div>
                )}
                {result.risks.length > 0 && (
                  <div><h3>Risks</h3><ul className="ai-risks">{result.risks.map((r, i) => <li key={i}>{r}{citations('risks', i)}</li>)}</ul></div>
                )}
              </div>
            )}

            <EvidenceSources evidence={result.evidence} scope={evidenceScope} />
            {result.prompt && (
              <div className="analyze-prompt-section">
                <button
                  className="analyze-prompt-toggle"
                  onClick={() => setShowPrompt((v) => !v)}
                >
                  {showPrompt ? 'Hide prompt' : 'Show prompt sent to the LLM'}
                </button>
                {showPrompt && (
                  <pre className="analyze-prompt">{result.prompt}</pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <ResearchHistory kind="analysis" refreshKey={historyKey} currentId={savedId} onOpen={reopen} />
    </div>
  );
}

export default AnalyzePage;
