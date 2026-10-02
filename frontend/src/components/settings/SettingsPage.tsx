import TagManager from './TagManager';
import OllamaSettings from './OllamaSettings';
import './SettingsPage.css';

function SettingsPage() {
  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
      </div>

      <div className="settings-content">
        <OllamaSettings />

        <TagManager />

        <div className="settings-section">
          <h2>Data Management</h2>
          <p className="coming-soon">Coming in Phase 5</p>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
