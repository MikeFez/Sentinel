import { useEffect, useState } from 'react';
import { Send, CheckCircle2, CircleDashed, XCircle } from 'lucide-react';
import { getNotifications, sendTestNotification, type SentNotification } from '../../api/client';
import { useAppData } from '../../state/useAppData';
import { ago } from '../../lib/format';

/** Destination status, test button and the latest notifications. The switches themselves are in
 *  AppSettings, so they save with the rest of the form. */
export function NotificationStatus() {
  const { toast } = useAppData();
  const [services, setServices] = useState<string[] | null>(null);
  const [recent, setRecent] = useState<SentNotification[]>([]);
  const [testing, setTesting] = useState(false);

  const load = () => getNotifications().then((r) => { setServices(r.services); setRecent(r.recent); }).catch(() => setServices([]));
  useEffect(() => { load(); }, []);

  const test = async () => {
    setTesting(true);
    try {
      const r = await sendTestNotification();
      toast(r.ok ? 'Test notification sent' : `Test failed: ${r.error}`, r.ok ? 'success' : 'error');
      await load();
    } catch {
      toast('Test failed: could not reach Sentinel', 'error');
    } finally {
      setTesting(false);
    }
  };

  if (services === null) return null;
  return (
    <>
      <div className={`md-status ${services.length ? 'md-good' : 'md-unknown'}`}>
        {services.length ? <CheckCircle2 size={18} /> : <CircleDashed size={18} />}
        <div>
          <strong>{services.length ? `Sending to ${services.join(', ')}` : 'No destinations yet'}</strong>
          <p className="muted">
            Set the <code>NOTIFY_URLS</code> environment variable to one or more{' '}
            <a href="https://github.com/caronc/apprise/wiki" target="_blank" rel="noopener noreferrer">Apprise URLs</a>{' '}
            (e.g. <code>ntfy://ntfy.sh/your-topic</code>, <code>pover://user@token</code>, <code>discord://id/token</code>),
            separated by spaces, then restart. Set <code>SENTINEL_URL</code> too for links back to the app.
          </p>
        </div>
        <button className="btn btn-secondary btn-sm ns-test" onClick={test} disabled={testing || !services.length}>
          <Send size={14} /> {testing ? 'Sending…' : 'Send test'}
        </button>
      </div>

      {recent.length > 0 && (
        <div className="ns-recent">
          <h3 className="settings-subhead">Recent</h3>
          <ul>
            {recent.slice(0, 8).map((n) => (
              <li key={n.id} title={n.error ?? n.body}>
                {n.status === 'sent' ? <CheckCircle2 size={14} className="ns-ok" /> : <XCircle size={14} className="ns-bad" />}
                <span className="ns-title">{n.title}</span>
                <span className="muted ns-when">{ago(n.at)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
