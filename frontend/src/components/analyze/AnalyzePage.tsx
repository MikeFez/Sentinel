import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, ArrowRight } from 'lucide-react';
import { runAnalysis, createCompany } from '../../api/client';
import { useAppData } from '../../state/AppData';
import type { AnalyzeResult } from '../../api/client';
import type { SentimentType } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed. Check the LLM endpoint is reachable.');
    } finally {
      setRunning(false);
    }
  };

  const stockData = result?.stock_data as Record<string, unknown> | null;

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
                {result.summary.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
            )}

            {(result.key_points.length > 0 || result.risks.length > 0) && (
              <div className="ai-lists">
                {result.key_points.length > 0 && (
                  <div><h3>Key points</h3><ul>{result.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul></div>
                )}
                {result.risks.length > 0 && (
                  <div><h3>Risks</h3><ul className="ai-risks">{result.risks.map((r, i) => <li key={i}>{r}</li>)}</ul></div>
                )}
              </div>
            )}

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
    </div>
  );
}

export default AnalyzePage;
