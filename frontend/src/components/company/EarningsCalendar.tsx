import { Calendar } from 'lucide-react';
import type { EarningsDate } from '../../types';
import './EarningsCalendar.css';

interface EarningsCalendarProps {
  earnings: EarningsDate[];
}

function EarningsCalendar({ earnings }: EarningsCalendarProps) {
  if (!earnings || earnings.length === 0) {
    return null;
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatEPS = (eps: number | undefined | null) => {
    if (eps == null) return 'N/A';
    return `$${eps.toFixed(2)}`;
  };

  return (
    <div className="earnings-calendar panel">
      <div className="panel-header">
        <Calendar size={20} />
        <h2>Earnings Calendar</h2>
      </div>

      <div className="earnings-list">
        {earnings.map((earning, index) => (
          <div key={index} className="earnings-item">
            <div className="earnings-date">
              <div className="earnings-date-value">{formatDate(earning.date)}</div>
              {earning.quarter && earning.year && (
                <div className="earnings-quarter">
                  Q{earning.quarter} {earning.year}
                </div>
              )}
            </div>

            <div className="earnings-details">
              {earning.epsEstimate != null && (
                <div className="earnings-metric">
                  <span className="earnings-metric-label">Est. EPS</span>
                  <span className="earnings-metric-value">
                    {formatEPS(earning.epsEstimate)}
                  </span>
                </div>
              )}

              {earning.epsActual != null && (
                <div className="earnings-metric">
                  <span className="earnings-metric-label">Actual EPS</span>
                  <span className="earnings-metric-value earnings-actual">
                    {formatEPS(earning.epsActual)}
                  </span>
                </div>
              )}

              {earning.epsActual != null &&
                earning.epsEstimate != null && (
                  <div className="earnings-surprise">
                    {earning.epsActual > earning.epsEstimate ? (
                      <span className="earnings-surprise-positive">
                        Beat by ${(earning.epsActual - earning.epsEstimate).toFixed(2)}
                      </span>
                    ) : earning.epsActual < earning.epsEstimate ? (
                      <span className="earnings-surprise-negative">
                        Missed by $
                        {(earning.epsEstimate - earning.epsActual).toFixed(2)}
                      </span>
                    ) : (
                      <span className="earnings-surprise-neutral">Met estimates</span>
                    )}
                  </div>
                )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default EarningsCalendar;
