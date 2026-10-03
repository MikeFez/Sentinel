import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { getThemes, type ThemeTrend } from '../../api/client';

/** Recurring themes in material news stories, with weekly counts over the last 8 weeks. */
function ThemesPanel({ companyId, refreshKey }: { companyId: string; refreshKey: string }) {
  const [themes, setThemes] = useState<ThemeTrend[]>([]);

  useEffect(() => {
    getThemes(companyId).then(setThemes).catch(() => setThemes([]));
  }, [companyId, refreshKey]);

  if (!themes.length) return null;
  const peak = Math.max(1, ...themes.flatMap((t) => t.weekly));
  return (
    <div className="card">
      <h2>Recurring themes <span className="muted themes-note">material stories, last 8 weeks</span></h2>
      <div className="themes">
        {themes.map((t) => (
          <div key={t.theme} className="theme-row">
            <span className="theme-name">{t.theme}{t.rising && <span className="theme-rising"><TrendingUp size={12} /> rising</span>}</span>
            <span className="theme-bars" aria-label={`${t.total} stories; weekly: ${t.weekly.join(', ')}`}>
              {t.weekly.map((n, i) => <span key={i} style={{ height: `${Math.max(8, (n / peak) * 100)}%` }} className={n ? 'on' : ''} />)}
            </span>
            <span className="muted num">{t.total}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ThemesPanel;
