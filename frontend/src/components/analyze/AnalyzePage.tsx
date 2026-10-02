import { useState } from 'react';
import { Sparkles, Search } from 'lucide-react';
import { runAnalysis } from '../../api/client';
import type { AnalyzeResult } from '../../api/client';
import type { SentimentType } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import './AnalyzePage.css';

function AnalyzePage() {
  const [ticker, setTicker] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [notes, setNotes] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [error, setError] = useState('');

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed. Check Ollama is running.');
    } finally {
      setRunning(false);
    }
  };

  const stockData = result?.stock_data as Record<string, unknown> | null;

  return (
    <div className="analyze-page">
      <div className="analyze-header">
        <div className="analyze-header-content">
          <Sparkles size={32} className="analyze-icon" />
          <div>
            <h1>Ad-hoc Analysis</h1>
            <p className="analyze-subtitle">
              Run a one-off AI analysis on any ticker or topic without saving it
            </p>
          </div>
        </div>
      </div>

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

            {result.prompt && (
              <div className="analyze-prompt-section">
                <button
                  className="analyze-prompt-toggle"
                  onClick={() => setShowPrompt((v) => !v)}
                >
                  {showPrompt ? 'Hide prompt' : 'Show prompt sent to Ollama'}
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
