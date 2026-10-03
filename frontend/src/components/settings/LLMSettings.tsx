import { useState, useEffect } from 'react';
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
        ai_prompt_instructions: promptInstructions,
      });
      alert('Settings saved successfully!');
      await checkHealth();
      await loadModels();
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
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
            Automatically re-sync public companies (with a ticker) when their data becomes stale
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
              Re-sync a company if its last completed sync is older than this many hours (1–168)
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
          <label htmlFor="prompt-instructions">AI Analysis Instructions</label>
          <textarea
            id="prompt-instructions"
            value={promptInstructions}
            onChange={(e) => setPromptInstructions(e.target.value)}
            rows={12}
            style={{ fontFamily: 'monospace', fontSize: '13px' }}
          />
          <small className="form-hint">
            These instructions are appended after the company data in every prompt sent to the LLM.
            The response must still contain <code>SUMMARY:</code> and <code>SENTIMENT:</code> sections
            for parsing to work.
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
