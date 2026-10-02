import { Link } from 'react-router-dom';
import { CalendarClock } from 'lucide-react';
import type { HomeSummary } from '../../api/client';
import './EarningsCountdown.css';

interface EarningsCountdownProps {
  earnings: HomeSummary['upcoming_earnings'];
}

function EarningsCountdown({ earnings }: EarningsCountdownProps) {
  if (earnings.length === 0) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const daysUntil = (dateStr: string) => {
    const d = new Date(dateStr);
    return Math.round((d.getTime() - today.getTime()) / 86400000);
  };

  const label = (days: number) => {
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days < 0) return `${Math.abs(days)}d ago`;
    return `in ${days}d`;
  };

  const urgency = (days: number) => {
    if (days <= 1) return 'urgent';
    if (days <= 7) return 'soon';
    return 'upcoming';
  };

  return (
    <div className="earnings-countdown">
      <h2 className="section-title">
        <CalendarClock size={20} />
        Upcoming Earnings
      </h2>
      <div className="earnings-list">
        {earnings.map((e, i) => {
          const days = daysUntil(e.date);
          return (
            <Link
              key={`${e.company_id}-${e.date}-${i}`}
              to={`/companies/${e.company_id}`}
              className={`earnings-item earnings-${urgency(days)}`}
            >
              <div className="earnings-company">
                <span className="earnings-name">{e.company_name}</span>
                {e.ticker && <span className="earnings-ticker">{e.ticker}</span>}
              </div>
              <div className="earnings-right">
                {e.quarter && e.year && (
                  <span className="earnings-period">Q{e.quarter} {e.year}</span>
                )}
                <span className={`earnings-days earnings-days--${urgency(days)}`}>
                  {label(days)}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default EarningsCountdown;
