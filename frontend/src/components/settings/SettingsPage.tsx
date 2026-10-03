import TagManager from './TagManager';
import LLMSettings from './LLMSettings';
import MarketDataSettings from './MarketDataSettings';
import './SettingsPage.css';

function SettingsPage() {
  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
      </div>

      <div className="settings-content">
        <LLMSettings />

        <TagManager />

        <MarketDataSettings />
      </div>
    </div>
  );
}

export default SettingsPage;
