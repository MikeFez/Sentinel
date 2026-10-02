import { useState, useEffect } from 'react';
import { RefreshCw, Check, X, AlertCircle } from 'lucide-react';
import {
  getSettings,
  updateSettings,
  getOllamaModels,
  checkOllamaHealth,
} from '../../api/client';
import './OllamaSettings.css';

function OllamaSettings() {
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [ollamaModel, setOllamaModel] = useState('');
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
      setOllamaUrl(settings.ollama_url || '');
      setOllamaModel(settings.ollama_model || '');
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
      const modelList = await getOllamaModels();
      setModels(modelList);
    } catch (error) {
      console.error('Failed to load Ollama models:', error);
      setModels([]);
    }
  };

  const checkHealth = async () => {
    setCheckingHealth(true);
    try {
      const status = await checkOllamaHealth();
      setHealthStatus(status);
    } catch (error) {
      console.error('Health check failed:', error);
      setHealthStatus({ healthy: false, url: ollamaUrl });
    } finally {
      setCheckingHealth(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings({
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel,
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
      <div className="ollama-settings">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="ollama-settings">
      <div className="settings-header-row">
        <h2>Ollama Configuration</h2>
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
          <label htmlFor="ollama-url">
            Ollama URL
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
            id="ollama-url"
            type="url"
            value={ollamaUrl}
            onChange={(e) => setOllamaUrl(e.target.value)}
            placeholder="http://athena.lan:11434"
          />
          <small className="form-hint">
            The URL where your Ollama instance is running (including port)
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="ollama-model">
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
              id="ollama-model"
              value={ollamaModel}
              onChange={(e) => setOllamaModel(e.target.value)}
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
                id="ollama-model"
                type="text"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                placeholder="qwen2.5:14b"
              />
              <div className="model-warning">
                <AlertCircle size={16} />
                <span>
                  Unable to fetch models from Ollama. You can still manually enter a model
                  name. Make sure Ollama is running and the URL is correct.
                </span>
              </div>
            </>
          )}
          <small className="form-hint">
            The Ollama model to use for analysis and summarization
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
            Show a red dot in the sidebar when a company's last sync is older than this many hours
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
            These instructions are appended after the company data in every prompt sent to Ollama.
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

export default OllamaSettings;
