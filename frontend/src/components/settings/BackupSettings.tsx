import { useRef, useState } from 'react';
import { Download, Upload } from 'lucide-react';
import { exportData, importData, errorDetail, type ExportFile, type ImportSummary } from '../../api/client';
import { useAppData } from '../../state/useAppData';

/** Export companies, tags and settings to a JSON file, or merge one in. */
function BackupSettings() {
  const { refresh, toast } = useAppData();
  const fileRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<{ name: string; data: ExportFile; preview: ImportSummary } | null>(null);
  const [includeSettings, setIncludeSettings] = useState(true);
  const [busy, setBusy] = useState(false);

  const download = async () => {
    try {
      const data = await exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `sentinel-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      toast('Export failed', 'error');
    }
  };

  const choose = async (file: File | undefined) => {
    if (!file) return;
    try {
      const data = JSON.parse(await file.text()) as ExportFile;
      const preview = await importData(data, includeSettings, true);
      setPending({ name: file.name, data, preview });
    } catch (err) {
      toast(err instanceof SyntaxError ? `${file.name} isn't valid JSON` : errorDetail(err, 'Could not read that file'), 'error');
    } finally {
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const confirm = async () => {
    if (!pending) return;
    setBusy(true);
    try {
      const r = await importData(pending.data, includeSettings, false);
      await refresh();
      toast(`Imported: ${r.created.length} added, ${r.updated.length} updated`, 'success');
      setPending(null);
    } catch (err) {
      toast(errorDetail(err, 'Import failed'), 'error');
    } finally {
      setBusy(false);
    }
  };

  const p = pending?.preview;
  return (
    <div className="settings-section">
      <div className="settings-header-row">
        <h2>Backup &amp; transfer</h2>
      </div>
      <p className="muted backup-text">
        Export your companies (positions, alerts, notes, tags), tags and settings as JSON. Importing merges a file in:
        companies with the same ticker or name are updated, new ones are added, and nothing is deleted. Sync history isn't included.
      </p>
      <div className="backup-actions">
        <button className="btn btn-secondary" onClick={download}><Download size={15} /> Export JSON</button>
        <button className="btn btn-secondary" onClick={() => fileRef.current?.click()}><Upload size={15} /> Import JSON…</button>
        <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={(e) => choose(e.target.files?.[0])} />
      </div>

      {pending && p && (
        <div className="backup-preview">
          <strong>{pending.name}</strong>
          {p.created.length + p.updated.length + p.tags_created === 0 ? (
            <p className="muted">Every company and tag in this file is already here.</p>
          ) : (
            <ul>
              {p.created.length > 0 && <li>Add {p.created.length}: {p.created.join(', ')}</li>}
              {p.updated.length > 0 && <li>Update {p.updated.length}: {p.updated.join(', ')}</li>}
              {p.tags_created > 0 && <li>{p.tags_created} new {p.tags_created === 1 ? 'tag' : 'tags'}</li>}
            </ul>
          )}
          <label className="backup-check">
            <input type="checkbox" checked={includeSettings} onChange={async (e) => {
              setIncludeSettings(e.target.checked);
              const preview = await importData(pending.data, e.target.checked, true);
              setPending({ ...pending, preview });
            }} />
            Also import settings{includeSettings && p.settings_changed ? ` (${p.settings_changed} would change)` : ''}
          </label>
          <div className="backup-actions">
            <button className="btn btn-primary" onClick={confirm} disabled={busy}>{busy ? 'Importing…' : 'Import'}</button>
            <button className="btn btn-secondary" onClick={() => setPending(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default BackupSettings;
