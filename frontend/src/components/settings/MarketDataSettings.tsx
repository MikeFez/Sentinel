import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, CircleDashed, RefreshCw } from 'lucide-react';
import { getFinnhubStatus, type FinnhubStatus } from '../../api/client';
import { ago } from '../../lib/format';

/** Whether Finnhub (prices, analyst ratings, insider trades, news) is working. */
function MarketDataSettings() {
  const [status, setStatus] = useState<FinnhubStatus | null>(null);
  const [checking, setChecking] = useState(false);

  const check = async (live: boolean) => {
    setChecking(live);
    try {
      setStatus(await getFinnhubStatus(live));
    } catch {
      setStatus({ configured: true, ok: false, error: 'Could not reach the Sentinel server', at: null });
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    check(false);
  }, []);

  const state = !status ? null : !status.configured || status.ok === false ? 'bad' : status.ok ? 'good' : 'unknown';

  return (
    <div className="settings-section market-data">
      <div className="settings-header-row">
        <h2>Market data (Finnhub)</h2>
        <button className="btn btn-secondary btn-sm" onClick={() => check(true)} disabled={checking}>
          <RefreshCw size={14} className={checking ? 'spinning' : ''} /> {checking ? 'Testing…' : 'Test connection'}
        </button>
      </div>
      {status && (
        <div className={`md-status md-${state}`}>
          {state === 'good' ? <CheckCircle2 size={18} /> : state === 'bad' ? <XCircle size={18} /> : <CircleDashed size={18} />}
          <div>
            <strong>
              {!status.configured ? 'No API key' : state === 'good' ? 'Working' : state === 'bad' ? 'Not working' : 'Not used yet since the server started'}
            </strong>
            <p className="muted">
              {status.error ?? (status.at ? `Last successful request ${ago(status.at)}.` : 'Test the connection to check it.')}
            </p>
          </div>
        </div>
      )}
      <small className="form-hint">
        The key comes from the <code>FINNHUB_API_KEY</code> environment variable. The free plan allows 60 requests a minute;
        a sync uses about seven per public company.
      </small>
    </div>
  );
}

export default MarketDataSettings;
