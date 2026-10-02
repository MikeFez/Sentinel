import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Briefcase } from 'lucide-react';
import { getCompanies } from '../../api/client';
import type { CompanyWithSync } from '../../types';
import SentimentBadge from '../shared/SentimentBadge';
import './PortfolioPage.css';

function PortfolioPage() {
  const [holdings, setHoldings] = useState<CompanyWithSync[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHoldings();
  }, []);

  const loadHoldings = async () => {
    try {
      const companies = await getCompanies();
      setHoldings(companies.filter((c) => c.shares_owned && c.shares_owned > 0));
    } catch (error) {
      console.error('Failed to load portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="portfolio-page">
        <div className="loading">Loading portfolio...</div>
      </div>
    );
  }

  if (holdings.length === 0) {
    return (
      <div className="portfolio-page">
        <div className="portfolio-header">
          <Briefcase size={32} className="portfolio-icon" />
          <div>
            <h1>Portfolio</h1>
            <p className="portfolio-subtitle">Track your stock positions</p>
          </div>
        </div>
        <div className="portfolio-empty">
          <Briefcase size={48} />
          <p>No positions yet</p>
          <p className="portfolio-empty-hint">
            Add shares owned to a company by clicking <strong>Edit</strong> on its detail page.
          </p>
        </div>
      </div>
    );
  }

  // Compute totals
  let totalValue = 0;
  let totalDayChange = 0;
  let totalDayChangePct: number | null = null;
  let validPriceCount = 0;

  const rows = holdings.map((company) => {
    const price = company.latest_sync?.stock_price ?? null;
    const changePct = company.latest_sync?.price_change ?? null;
    const shares = company.shares_owned!;
    const value = price != null ? price * shares : null;

    if (value != null) {
      totalValue += value;
      validPriceCount++;
    }
    if (price != null && changePct != null) {
      totalDayChange += price * shares * (changePct / 100);
    }

    return { company, price, changePct, shares, value };
  });

  if (validPriceCount > 0 && totalValue > 0) {
    totalDayChangePct = (totalDayChange / (totalValue - totalDayChange)) * 100;
  }

  const fmt = (n: number) =>
    n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  return (
    <div className="portfolio-page">
      <div className="portfolio-header">
        <div className="portfolio-header-content">
          <Briefcase size={32} className="portfolio-icon" />
          <div>
            <h1>Portfolio</h1>
            <p className="portfolio-subtitle">{holdings.length} position{holdings.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        {totalValue > 0 && (
          <div className="portfolio-total">
            <div className="portfolio-total-value">{fmt(totalValue)}</div>
            {totalDayChangePct != null && (
              <div className={`portfolio-total-change ${totalDayChange >= 0 ? 'up' : 'down'}`}>
                {totalDayChange >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {totalDayChange >= 0 ? '+' : ''}{fmt(totalDayChange)} ({totalDayChangePct >= 0 ? '+' : ''}{totalDayChangePct.toFixed(2)}% today)
              </div>
            )}
          </div>
        )}
      </div>

      <div className="portfolio-table-wrapper">
        <table className="portfolio-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Shares</th>
              <th>Price</th>
              <th>Today</th>
              <th>Value</th>
              <th>Sentiment</th>
              <th>Alerts</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ company, price, changePct, shares, value }) => (
              <tr key={company.id}>
                <td>
                  <Link to={`/companies/${company.id}`} className="portfolio-company-link">
                    <span className="portfolio-company-name">{company.name}</span>
                    {company.ticker && (
                      <span className="portfolio-ticker">{company.ticker}</span>
                    )}
                  </Link>
                </td>
                <td className="portfolio-num">{shares.toLocaleString()}</td>
                <td className="portfolio-num">
                  {price != null ? `$${price.toFixed(2)}` : '—'}
                </td>
                <td className="portfolio-num">
                  {changePct != null ? (
                    <span className={changePct >= 0 ? 'up' : 'down'}>
                      {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                    </span>
                  ) : '—'}
                </td>
                <td className="portfolio-num portfolio-value">
                  {value != null ? fmt(value) : '—'}
                </td>
                <td>
                  {company.latest_sync?.ai_sentiment ? (
                    <SentimentBadge sentiment={company.latest_sync.ai_sentiment} />
                  ) : '—'}
                </td>
                <td className="portfolio-alerts">
                  {company.alert_above != null && (
                    <span className="alert-chip alert-above" title="Alert above">
                      ↑ ${company.alert_above.toFixed(2)}
                    </span>
                  )}
                  {company.alert_below != null && (
                    <span className="alert-chip alert-below" title="Alert below">
                      ↓ ${company.alert_below.toFixed(2)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PortfolioPage;
