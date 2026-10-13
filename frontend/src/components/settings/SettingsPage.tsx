import TagManager from './TagManager';
import AppSettings from './AppSettings';
import MarketDataSettings from './MarketDataSettings';
import BackupSettings from './BackupSettings';
import './SettingsPage.css';
import { useTitle } from '../../lib/useTitle';

const SECTIONS = [
  { id: 'ai-model', label: 'AI model' },
  { id: 'ai-analysis', label: 'AI analysis' },
  { id: 'refresh', label: 'Refresh & re-analysis' },
  { id: 'prices', label: 'Prices & history' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'tags', label: 'Tags' },
  { id: 'market-data', label: 'Market data' },
  { id: 'backup', label: 'Backup' },
];

function SettingsPage() {
  useTitle('Settings');
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
        <nav className="settings-nav" aria-label="Settings sections">
          {SECTIONS.map((s) => <button key={s.id} className="settings-nav-item" onClick={() => jump(s.id)}>{s.label}</button>)}
        </nav>
      </div>

      <div className="settings-content">
        <AppSettings />
        <div id="tags"><TagManager /></div>
        <div id="market-data"><MarketDataSettings /></div>
        <div id="backup"><BackupSettings /></div>
      </div>
    </div>
  );
}

export default SettingsPage;
