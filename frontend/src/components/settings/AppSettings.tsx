import { useState, useEffect, type ReactNode } from 'react';
import { useAppData } from '../../state/useAppData';
import { RefreshCw, Check, X, AlertCircle } from 'lucide-react';
import { getSettings, updateSettings, getLLMModels, checkLLMHealth } from '../../api/client';
import './AppSettings.css';
import { NotificationStatus } from './NotificationSettings';
import { NOTIFY_EVENTS, DIGEST_DAYS } from '../../lib/notifications';

type Values = Record<string, string>;

// Every setting edited on this page; saved together with one Save
const KEYS = [
  'llm_base_url', 'llm_model', 'analysis_mode', 'llm_reasoning_effort', 'llm_max_tokens',
  'ai_prompt_instructions', 'filings_enabled', 'news_count',
  'auto_refresh_enabled', 'auto_refresh_hours', 'private_refresh_days', 'staleness_hours',
  'move_sync_percent', 'analysis_drift_percent', 'earnings_sync', 'signal_sync',
  'price_refresh_minutes', 'history_detail_days',
  'notify_price_alerts', 'notify_big_moves', 'notify_sentiment_flips', 'notify_earnings', 'notify_material_news',
  'notify_filings', 'notify_problems', 'notify_digest', 'notify_digest_day',
] as const;

/** "5.0" → "5": stored numbers come back as floats. */
const tidy = (v: string) => (/^-?\d+\.0+$/.test(v) ? v.replace(/\.0+$/, '') : v);

function Field({ id, label, hint, children }: { id: string; label: ReactNode; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <small className="form-hint">{hint}</small>}
    </div>
  );
}

function Toggle({ id, on, onChange }: { id: string; on: boolean; onChange: (on: boolean) => void }) {
  return (
    <div className="toggle-row">
      <button id={id} type="button" role="switch" aria-checked={on} className={`toggle-switch ${on ? 'on' : ''}`} onClick={() => onChange(!on)}>
        <span className="toggle-thumb" />
      </button>
      <span className="toggle-label">{on ? 'On' : 'Off'}</span>
    </div>
  );
}

/** The app's settings, in sections, with one save bar that appears when something changed. */
function AppSettings() {
  const { toast, refresh } = useAppData();
  const [saved, setSaved] = useState<Values | null>(null);
  const [values, setValues] = useState<Values>({});
  const [models, setModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [health, setHealth] = useState<{ healthy: boolean } | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  const dirtyKeys = saved ? KEYS.filter((k) => (values[k] ?? '') !== (saved[k] ?? '')) : [];
  const dirty = dirtyKeys.length > 0;

  const set = (key: string) => (value: string) => setValues((v) => ({ ...v, [key]: value }));
  const flag = (key: string) => values[key] === 'true';
  const setFlag = (key: string) => (on: boolean) => set(key)(on ? 'true' : 'false');
  const input = (key: string) => ({ id: key, value: values[key] ?? '', onChange: (e: { target: { value: string } }) => set(key)(e.target.value) });

  const loadModels = async () => {
    try {
      setModels(await getLLMModels());
    } catch {
      setModels([]);
    }
  };

  const checkHealth = async () => {
    setCheckingHealth(true);
    try {
      setHealth(await checkLLMHealth());
    } catch {
      setHealth({ healthy: false });
    } finally {
      setCheckingHealth(false);
    }
  };

  useEffect(() => {
    getSettings()
      .then((s) => {
        const v = Object.fromEntries(KEYS.map((k) => [k, tidy(s[k] ?? '')]));
        setSaved(v);
        setValues(v);
      })
      .catch(() => toast('Could not load settings', 'error'));
    loadModels();
    checkHealth();
    // Load once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Warn before closing the tab with unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const save = async () => {
    setSaving(true);
    try {
      const changed = Object.fromEntries(dirtyKeys.map((k) => [k, (values[k] ?? '').trim()]));
      const after = await updateSettings(changed);
      const v = Object.fromEntries(KEYS.map((k) => [k, tidy(after[k] ?? '')]));
      setSaved(v);
      setValues(v);
      toast('Settings saved', 'success');
      if ('llm_base_url' in changed || 'llm_model' in changed) {
        await checkHealth();
        await loadModels();
      }
      await refresh(); // staleness and drift thresholds are used across the app
    } catch {
      toast('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (!saved) return <div className="settings-section"><div className="loading">Loading…</div></div>;

  return (
    <>
      <section id="ai-model" className="settings-section">
        <div className="settings-header-row">
          <h2>AI model</h2>
          {health && (
            <div className={`health-badge ${health.healthy ? 'healthy' : 'unhealthy'}`}>
              {health.healthy ? <><Check size={16} /> Connected</> : <><X size={16} /> Disconnected</>}
            </div>
          )}
        </div>
        <div className="settings-form">
          <Field id="llm_base_url"
            label={<>Endpoint URL <button type="button" className="refresh-button" onClick={checkHealth} disabled={checkingHealth} title="Check connection"><RefreshCw size={14} className={checkingHealth ? 'spinning' : ''} /></button></>}
            hint="OpenAI-compatible base URL, including /v1. The API key comes from the LLM_API_KEY environment variable.">
            <input type="url" placeholder="http://athena.lan:8090/v1" {...input('llm_base_url')} />
          </Field>
          <Field id="llm_model"
            label={<>Model <button type="button" className="refresh-button" onClick={loadModels} title="Refresh model list"><RefreshCw size={14} /></button></>}>
            {models.length > 0 ? (
              <select {...input('llm_model')}>
                {!models.includes(values.llm_model) && values.llm_model && <option value={values.llm_model}>{values.llm_model}</option>}
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            ) : (
              <>
                <input type="text" placeholder="qwen3.8:27b" {...input('llm_model')} />
                <div className="model-warning">
                  <AlertCircle size={16} />
                  <span>Couldn't list the endpoint's models. You can still type a model name; check that the server is running and the URL is right.</span>
                </div>
              </>
            )}
          </Field>
          <Field id="analysis_mode" label="Analysis style"
            hint="The debate writes the strongest bull and bear cases, then a verdict that weighs them. It's more balanced but takes 2–3× as long.">
            <select {...input('analysis_mode')}>
              <option value="debate">Bull vs. bear debate (3 LLM calls per analysis)</option>
              <option value="single">Single pass (1 LLM call)</option>
            </select>
          </Field>
          <div className="settings-pair">
            <Field id="llm_reasoning_effort" label={<>Reasoning effort <span className="optional">(optional)</span></>}
              hint={<>Sent as <code>reasoning_effort</code>, e.g. <code>low</code> or <code>medium</code>. Lower is much faster. Leave empty if your server doesn't support it.</>}>
              <input type="text" placeholder="Server default" {...input('llm_reasoning_effort')} />
            </Field>
            <Field id="llm_max_tokens" label="Output token budget"
              hint="The longest reply per call, reasoning included (sent as max_tokens; 0 = server default). It's not the context size: keep it below the server's per-slot context minus the prompt.">
              <input type="number" min="0" step="1024" {...input('llm_max_tokens')} />
            </Field>
          </div>
        </div>
      </section>

      <section id="ai-analysis" className="settings-section">
        <div className="settings-header-row"><h2>AI analysis</h2></div>
        <div className="settings-form">
          <Field id="ai_prompt_instructions" label="Analysis instructions"
            hint="Guidance added after the company data in every analysis prompt. Sentinel sets the response format and what each sentiment means, so you don't need to.">
            <textarea rows={7} className="mono-textarea" {...input('ai_prompt_instructions')} />
          </Field>
          <Field id="filings_enabled" label="Summarize SEC filings"
            hint={<>Once a day, summarize new 8-K, 10-Q and 10-K filings for public companies (annual reports also list risk factors new since last year). Summaries feed into the analysis. Needs the <code>SEC_USER_AGENT</code> environment variable ("Your Name you@example.com").</>}>
            <Toggle id="filings_enabled" on={flag('filings_enabled')} onChange={setFlag('filings_enabled')} />
          </Field>
        </div>
      </section>

      <section id="refresh" className="settings-section">
        <div className="settings-header-row"><h2>Refresh &amp; re-analysis</h2></div>
        <div className="settings-form">
          <Field id="auto_refresh_enabled" label="Scheduled refresh" hint="Re-sync companies automatically when their data gets old.">
            <Toggle id="auto_refresh_enabled" on={flag('auto_refresh_enabled')} onChange={setFlag('auto_refresh_enabled')} />
          </Field>
          {flag('auto_refresh_enabled') && (
            <div className="settings-pair">
              <Field id="auto_refresh_hours" label="Public companies (hours)" hint="Re-sync when the last sync is older than this.">
                <input type="number" min="1" max="168" {...input('auto_refresh_hours')} />
              </Field>
              <Field id="private_refresh_days" label="Private companies (days)" hint="They only have news, so a slower schedule. 0 = never automatically.">
                <input type="number" min="0" max="365" {...input('private_refresh_days')} />
              </Field>
            </div>
          )}
          <Field id="staleness_hours" label="Flag data as stale after (hours)" hint='Shown in the sidebar and dashboard; "Sync stale" refreshes these.'>
            <input type="number" min="1" max="720" {...input('staleness_hours')} />
          </Field>
          <h3 className="settings-subhead">Re-analyze when something happens</h3>
          <div className="settings-pair">
            <Field id="move_sync_percent" label="Big daily move (%)" hint="A public company moves this much in a day; at most once per trading day. 0 = off.">
              <input type="number" min="0" max="50" step="0.5" {...input('move_sync_percent')} />
            </Field>
            <Field id="analysis_drift_percent" label="Drift since the last analysis (%)"
              hint="The price is this far from where the last analysis was written; analyses this far off are also flagged. 0 = off.">
              <input type="number" min="0" max="100" step="1" {...input('analysis_drift_percent')} />
            </Field>
          </div>
          <div className="settings-pair">
            <Field id="earnings_sync" label="After earnings" hint="Once results are out (after 4:30 PM ET on the earnings date).">
              <Toggle id="earnings_sync" on={flag('earnings_sync')} onChange={setFlag('earnings_sync')} />
            </Field>
            <Field id="signal_sync" label="Analyst or insider changes" hint="Checked daily: 3+ ratings shift or a new consensus, or an insider trades $1M+.">
              <Toggle id="signal_sync" on={flag('signal_sync')} onChange={setFlag('signal_sync')} />
            </Field>
          </div>
        </div>
      </section>

      <section id="prices" className="settings-section">
        <div className="settings-header-row"><h2>Prices &amp; history</h2></div>
        <div className="settings-form">
          <div className="settings-pair">
            <Field id="price_refresh_minutes" label="Price refresh (minutes)" hint="While the US market is open, plus once after the close. 0 = off.">
              <input type="number" min="0" max="120" {...input('price_refresh_minutes')} />
            </Field>
            <Field id="news_count" label="News articles per sync" hint="1–50.">
              <input type="number" min="1" max="50" {...input('news_count')} />
            </Field>
          </div>
          <Field id="history_detail_days" label="Keep full sync detail (days)"
            hint="Older syncs keep their price and analysis but drop news, prompts and insider data. Each company's newest sync is always kept in full. 0 = keep everything.">
            <input type="number" min="0" max="3650" {...input('history_detail_days')} />
          </Field>
        </div>
      </section>

      <section id="notifications" className="settings-section">
        <div className="settings-header-row"><h2>Notifications</h2></div>
        <div className="settings-form">
          <NotificationStatus />
          <h3 className="settings-subhead">Send me</h3>
          <div className="notify-grid">
            {NOTIFY_EVENTS.map((e) => (
              <Field key={e.kind} id={`notify_${e.kind}`} label={e.label} hint={e.hint}>
                <Toggle id={`notify_${e.kind}`} on={flag(`notify_${e.kind}`)} onChange={setFlag(`notify_${e.kind}`)} />
              </Field>
            ))}
          </div>
          {flag('notify_digest') && (
            <Field id="notify_digest_day" label="Weekly digest day" hint="Sent at 8 AM New York time.">
              <select {...input('notify_digest_day')}>
                {DIGEST_DAYS.map((d) => <option key={d} value={d}>{d[0].toUpperCase() + d.slice(1)}</option>)}
              </select>
            </Field>
          )}
        </div>
      </section>

      {dirty && (
        <div className="settings-savebar" role="region" aria-label="Unsaved changes">
          <span>{dirtyKeys.length} unsaved {dirtyKeys.length === 1 ? 'change' : 'changes'}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => setValues(saved)} disabled={saving}>Discard</button>
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
        </div>
      )}
    </>
  );
}

export default AppSettings;
