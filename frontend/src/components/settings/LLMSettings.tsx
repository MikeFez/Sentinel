import { useState, useEffect } from 'react';
import { useAppData } from '../../state/useAppData';
import { RefreshCw, Check, X, AlertCircle } from 'lucide-react';
import {
  getSettings,
  updateSettings,
  getLLMModels,
  checkLLMHealth,
} from '../../api/client';
import './LLMSettings.css';

function LLMSettings() {
  const [llmBaseUrl, setLlmBaseUrl] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [newsCount, setNewsCount] = useState('10');
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [autoRefreshHours, setAutoRefreshHours] = useState('24');
  const [stalenessHours, setStalenessHours] = useState('24');
  const [priceMinutes, setPriceMinutes] = useState('5');
  const [privateDays, setPrivateDays] = useState('7');
  const [historyDays, setHistoryDays] = useState('30');
  const [moveSyncPercent, setMoveSyncPercent] = useState('5');
  const [earningsSync, setEarningsSync] = useState(true);
  const [signalSync, setSignalSync] = useState(true);
  const [analysisMode, setAnalysisMode] = useState('debate');
  const [reasoningEffort, setReasoningEffort] = useState('');
  const [filingsEnabled, setFilingsEnabled] = useState(true);
  const { toast } = useAppData();
  const [promptInstructions, setPromptInstructions] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [healthStatus, setHealthStatus] = useState<{
    healthy: boolean;
    url: string;
  } | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  useEffect(() => {
    loadSettings();
    checkHealth();
    // Load once on mount; both functions only read settings from the server
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await getSettings();
      setLlmBaseUrl(settings.llm_base_url || '');
      setLlmModel(settings.llm_model || '');
      setNewsCount(settings.news_count || '10');
      setAutoRefreshEnabled(settings.auto_refresh_enabled === 'true');
      setAutoRefreshHours(settings.auto_refresh_hours || '24');
      setStalenessHours(settings.staleness_hours || '24');
      setPriceMinutes(settings.price_refresh_minutes ?? '5');
      setPrivateDays(settings.private_refresh_days ?? '7');
      setHistoryDays(settings.history_detail_days ?? '30');
      setMoveSyncPercent(settings.move_sync_percent ?? '5');
      setEarningsSync(settings.earnings_sync !== 'false');
      setSignalSync(settings.signal_sync !== 'false');
      setAnalysisMode(settings.analysis_mode || 'debate');
      setReasoningEffort(settings.llm_reasoning_effort ?? '');
      setFilingsEnabled(settings.filings_enabled !== 'false');
      setPromptInstructions(settings.ai_prompt_instructions || '');
      await loadModels();
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const modelList = await getLLMModels();
      setModels(modelList);
    } catch (error) {
      console.error('Failed to load LLM models:', error);
      setModels([]);
    }
  };

  const checkHealth = async () => {
    setCheckingHealth(true);
    try {
      const status = await checkLLMHealth();
      setHealthStatus(status);
    } catch (error) {
      console.error('Health check failed:', error);
      setHealthStatus({ healthy: false, url: llmBaseUrl });
    } finally {
      setCheckingHealth(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings({
        llm_base_url: llmBaseUrl,
        llm_model: llmModel,
        news_count: newsCount,
        auto_refresh_enabled: autoRefreshEnabled ? 'true' : 'false',
        auto_refresh_hours: autoRefreshHours,
        staleness_hours: stalenessHours,
        price_refresh_minutes: priceMinutes,
        private_refresh_days: privateDays,
        history_detail_days: historyDays,
        move_sync_percent: moveSyncPercent,
        earnings_sync: earningsSync ? 'true' : 'false',
        signal_sync: signalSync ? 'true' : 'false',
        analysis_mode: analysisMode,
        llm_reasoning_effort: reasoningEffort.trim(),
        filings_enabled: filingsEnabled ? 'true' : 'false',
        ai_prompt_instructions: promptInstructions,
      });
      toast('Settings saved', 'success');
      await checkHealth();
      await loadModels();
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="llm-settings">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="llm-settings">
      <div className="settings-header-row">
        <h2>LLM Configuration</h2>
        {healthStatus && (
          <div className={`health-badge ${healthStatus.healthy ? 'healthy' : 'unhealthy'}`}>
            {healthStatus.healthy ? (
              <>
                <Check size={16} />
                Connected
              </>
            ) : (
              <>
                <X size={16} />
                Disconnected
              </>
            )}
          </div>
        )}
      </div>

      <div className="settings-form">
        <div className="form-group">
          <label htmlFor="llm-url">
            LLM Endpoint URL
            <button
              type="button"
              className="refresh-button"
              onClick={checkHealth}
              disabled={checkingHealth}
              title="Check connection"
            >
              <RefreshCw size={14} className={checkingHealth ? 'spinning' : ''} />
            </button>
          </label>
          <input
            id="llm-url"
            type="url"
            value={llmBaseUrl}
            onChange={(e) => setLlmBaseUrl(e.target.value)}
            placeholder="http://athena.lan:8090/v1"
          />
          <small className="form-hint">
            OpenAI-compatible base URL, including /v1 (e.g. http://athena.lan:8090/v1). The API key comes from the LLM_API_KEY env var.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="llm-model">
            Model
            <button
              type="button"
              className="refresh-button"
              onClick={loadModels}
              title="Refresh model list"
            >
              <RefreshCw size={14} />
            </button>
          </label>
          {models.length > 0 ? (
            <select
              id="llm-model"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          ) : (
            <>
              <input
                id="llm-model"
                type="text"
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                placeholder="qwen2.5:14b"
              />
              <div className="model-warning">
                <AlertCircle size={16} />
                <span>
                  Unable to fetch models from the endpoint. You can still manually enter a model
                  name. Make sure the server is running and the URL is correct.
                </span>
              </div>
            </>
          )}
          <small className="form-hint">
            The model to use for analysis and summarization
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="analysis-mode">Analysis Style</label>
          <select id="analysis-mode" value={analysisMode} onChange={(e) => setAnalysisMode(e.target.value)}>
            <option value="debate">Bull vs. bear debate (3 LLM calls per analysis)</option>
            <option value="single">Single pass (1 LLM call)</option>
          </select>
          <small className="form-hint">
            The debate writes the strongest bull and bear cases, then a verdict that weighs them. It's more balanced
            but takes 2–3× as long. The calls run one at a time, so a shared LLM keeps a slot free.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="reasoning-effort">Reasoning Effort <span className="optional">(optional)</span></label>
          <input id="reasoning-effort" type="text" value={reasoningEffort} placeholder="Server default" onChange={(e) => setReasoningEffort(e.target.value)} />
          <small className="form-hint">
            Sent as <code>reasoning_effort</code> to reasoning models, e.g. <code>low</code> or <code>medium</code>.
            Lower is much faster. Leave empty if your server doesn't support it; invalid values can make every request fail.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="filings-toggle">Summarize SEC Filings</label>
          <div className="toggle-row">
            <button id="filings-toggle" type="button" role="switch" aria-checked={filingsEnabled}
              className={`toggle-switch ${filingsEnabled ? 'on' : ''}`} onClick={() => setFilingsEnabled((v) => !v)}>
              <span className="toggle-thumb" />
            </button>
            <span className="toggle-label">{filingsEnabled ? 'Enabled' : 'Disabled'}</span>
          </div>
          <small className="form-hint">
            Once a day, find new 8-K, 10-Q and 10-K filings for public companies and summarize them; annual reports also
            list risk factors that are new since the previous year. Summaries feed into the AI analysis. Set
            the <code>SEC_USER_AGENT</code> environment variable to "YourName your@email" (SEC asks for a contact).
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="news-count">News Article Count</label>
          <input
            id="news-count"
            type="number"
            min="1"
            max="50"
            value={newsCount}
            onChange={(e) => setNewsCount(e.target.value)}
          />
          <small className="form-hint">
            Number of news articles to fetch per sync (1-50)
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="auto-refresh-toggle">Auto Refresh</label>
          <div className="toggle-row">
            <button
              id="auto-refresh-toggle"
              type="button"
              role="switch"
              aria-checked={autoRefreshEnabled}
              className={`toggle-switch ${autoRefreshEnabled ? 'on' : ''}`}
              onClick={() => setAutoRefreshEnabled((v) => !v)}
            >
              <span className="toggle-thumb" />
            </button>
            <span className="toggle-label">
              {autoRefreshEnabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <small className="form-hint">
            Automatically re-sync companies when their data becomes stale
          </small>
        </div>

        {autoRefreshEnabled && (
          <div className="form-group">
            <label htmlFor="auto-refresh-hours">Refresh Interval (hours)</label>
            <input
              id="auto-refresh-hours"
              type="number"
              min="1"
              max="168"
              value={autoRefreshHours}
              onChange={(e) => setAutoRefreshHours(e.target.value)}
            />
            <small className="form-hint">
              Re-sync a public company if its last completed sync is older than this many hours (1–168)
            </small>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="staleness-hours">Staleness Threshold (hours)</label>
          <input
            id="staleness-hours"
            type="number"
            min="1"
            max="720"
            value={stalenessHours}
            onChange={(e) => setStalenessHours(e.target.value)}
          />
          <small className="form-hint">
            Data older than this many hours counts as stale: it's flagged in the sidebar and dashboard, and "Sync stale" refreshes it
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="private-days">Private Company Refresh (days)</label>
          <input id="private-days" type="number" min="0" max="365" value={privateDays} onChange={(e) => setPrivateDays(e.target.value)} />
          <small className="form-hint">
            Private and pre-IPO companies only have news, so they refresh on this slower schedule. 0 never refreshes them automatically.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="move-percent">Re-analyze on Big Moves (%)</label>
          <input id="move-percent" type="number" min="0" max="50" step="0.5" value={moveSyncPercent} onChange={(e) => setMoveSyncPercent(e.target.value)} />
          <small className="form-hint">
            Run a full sync (news and AI analysis) when a public company's price moves at least this much in a day, at most once per trading day. 0 turns it off.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="earnings-toggle">Re-analyze After Earnings</label>
          <div className="toggle-row">
            <button id="earnings-toggle" type="button" role="switch" aria-checked={earningsSync}
              className={`toggle-switch ${earningsSync ? 'on' : ''}`} onClick={() => setEarningsSync((v) => !v)}>
              <span className="toggle-thumb" />
            </button>
            <span className="toggle-label">{earningsSync ? 'Enabled' : 'Disabled'}</span>
          </div>
          <small className="form-hint">Sync a company once its results are out (after 4:30 PM ET on its earnings date).</small>
        </div>

        <div className="form-group">
          <label htmlFor="signal-toggle">Re-analyze on Analyst or Insider Changes</label>
          <div className="toggle-row">
            <button id="signal-toggle" type="button" role="switch" aria-checked={signalSync}
              className={`toggle-switch ${signalSync ? 'on' : ''}`} onClick={() => setSignalSync((v) => !v)}>
              <span className="toggle-thumb" />
            </button>
            <span className="toggle-label">{signalSync ? 'Enabled' : 'Disabled'}</span>
          </div>
          <small className="form-hint">
            Checked once a day per public company: sync when analyst ratings shift (3+ ratings or a new consensus) or an insider buys or sells $1M+ on the open market.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="price-minutes">Price Refresh (minutes)</label>
          <input id="price-minutes" type="number" min="0" max="120" value={priceMinutes} onChange={(e) => setPriceMinutes(e.target.value)} />
          <small className="form-hint">
            How often to update prices (no news or AI analysis) while the US market is open, plus once after the close. 0 turns it off.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="history-days">Keep Full Sync Detail (days)</label>
          <input id="history-days" type="number" min="0" max="3650" value={historyDays} onChange={(e) => setHistoryDays(e.target.value)} />
          <small className="form-hint">
            Older syncs keep their price and analysis but drop news, prompts and insider data to keep the database small. Each company's newest sync is always kept in full. 0 keeps everything.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="prompt-instructions">AI Analysis Instructions</label>
          <textarea
            id="prompt-instructions"
            value={promptInstructions}
            onChange={(e) => setPromptInstructions(e.target.value)}
            rows={7}
            style={{ fontFamily: 'monospace', fontSize: '13px' }}
          />
          <small className="form-hint">
            Guidance added after the company data in every analysis prompt. The response format (summary,
            sentiment, key points, risks, what changed) is set by Sentinel, so you don't need to describe it here.
          </small>
        </div>

        <div className="form-actions">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default LLMSettings;
