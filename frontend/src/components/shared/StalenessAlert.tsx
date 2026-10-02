import { AlertTriangle, Clock } from 'lucide-react';
import type { Sync } from '../../types';
import './StalenessAlert.css';

interface StalenessAlertProps {
  sync: Sync | null | undefined;
}

function StalenessAlert({ sync }: StalenessAlertProps) {
  if (!sync) {
    return (
      <div className="staleness-alert alert-error">
        <AlertTriangle size={20} />
        <div>
          <strong>No data available</strong>
          <p>This company has never been synced. Click "Sync Now" to fetch data.</p>
        </div>
      </div>
    );
  }

  const syncDate = new Date(sync.synced_at);
  const now = new Date();
  const diffMs = now.getTime() - syncDate.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  // Don't show alert if synced within last 24 hours
  if (diffHours < 24) {
    return null;
  }

  const severity = diffDays >= 7 ? 'error' : 'warning';
  const timeAgo =
    diffDays === 1
      ? '1 day ago'
      : diffDays < 7
      ? `${diffDays} days ago`
      : diffDays < 30
      ? `${diffDays} days ago`
      : `${Math.floor(diffDays / 30)} months ago`;

  return (
    <div className={`staleness-alert alert-${severity}`}>
      <Clock size={20} />
      <div>
        <strong>
          {severity === 'error' ? 'Data is very stale' : 'Data needs refresh'}
        </strong>
        <p>Last refreshed {timeAgo}. Consider running a new sync.</p>
      </div>
    </div>
  );
}

export default StalenessAlert;
