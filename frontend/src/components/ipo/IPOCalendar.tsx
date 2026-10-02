import { useState, useEffect } from 'react';
import { Calendar, RefreshCw, TrendingUp, BookmarkPlus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getIPOCalendar, refreshIPOCalendar, createCompany } from '../../api/client';
import type { IPOEntry } from '../../types';
import './IPOCalendar.css';

function IPOCalendar() {
  const [ipos, setIpos] = useState<IPOEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showWithdrawn, setShowWithdrawn] = useState(false);
  const [showPast, setShowPast] = useState(false);
  const [watchedIds, setWatchedIds] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  useEffect(() => {
    loadIPOs();
  }, []);

  const loadIPOs = async () => {
    try {
      const data = await getIPOCalendar();
      setIpos(data);
    } catch (error) {
      console.error('Failed to load IPO calendar:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshIPOCalendar();
      await loadIPOs();
    } catch (error) {
      console.error('Failed to refresh IPO calendar:', error);
      alert('Failed to refresh IPO calendar');
    } finally {
      setRefreshing(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const formatDaysFromNow = (dateStr: string) => {
    const diff = Math.round((new Date(dateStr).getTime() - today.getTime()) / 86400000);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff === -1) return 'Yesterday';
    if (diff < 0) return `${Math.abs(diff)}d ago`;
    return `${diff}d`;
  };

  const formatPriceRange = (low: number | null, high: number | null) => {
    if (!low && !high) return '—';
    if (low && high) return `$${low.toFixed(2)}–$${high.toFixed(2)}`;
    if (low) return `$${low.toFixed(2)}`;
    if (high) return `$${high.toFixed(2)}`;
    return '—';
  };

  const formatShares = (shares: number | null) => {
    if (!shares) return '—';
    if (shares >= 1_000_000) return (shares / 1_000_000).toFixed(1) + 'M';
    if (shares >= 1_000) return (shares / 1_000).toFixed(0) + 'K';
    return shares.toString();
  };

  const formatDealSize = (value: number | null) => {
    if (!value) return '—';
    if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
    return `$${value.toLocaleString()}`;
  };

  const formatLockupExpiry = (dateStr: string) => {
    const expiry = new Date(new Date(dateStr).getTime() + 180 * 86400000);
    return expiry.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleWatch = async (ipo: IPOEntry) => {
    try {
      const status = ipo.status?.toLowerCase();
      const companyStatus = (status === 'listed' || status === 'priced') ? 'public' : 'pre_ipo';
      const company = await createCompany({
        name: ipo.name,
        ticker: ipo.symbol || undefined,
        status: companyStatus,
      });
      setWatchedIds((prev) => new Set([...prev, ipo.id]));
      navigate(`/companies/${company.id}`);
    } catch (error) {
      console.error('Failed to add company to watchlist:', error);
      alert('Failed to add to watchlist');
    }
  };

  if (loading) {
    return (
      <div className="ipo-calendar">
        <div className="loading">Loading IPO calendar...</div>
      </div>
    );
  }

  const isPast = (ipo: IPOEntry) => new Date(ipo.date) < today;
  const isWithdrawn = (ipo: IPOEntry) => ipo.status?.toLowerCase() === 'withdrawn';

  const withdrawnCount = ipos.filter(isWithdrawn).length;
  const pastCount = ipos.filter((ipo) => isPast(ipo) && !isWithdrawn(ipo)).length;

  const sortedIPOs = [...ipos]
    .filter((ipo) => (showWithdrawn || !isWithdrawn(ipo)) && (showPast || !isPast(ipo)))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <div className="ipo-calendar">
      <div className="ipo-header">
        <div className="ipo-header-content">
          <Calendar size={32} className="ipo-icon" />
          <div>
            <h1>Upcoming IPOs</h1>
            <p className="ipo-subtitle">Track upcoming initial public offerings</p>
          </div>
        </div>
        <div className="ipo-header-actions">
          {pastCount > 0 && (
            <button
              className={`btn btn-secondary ${showPast ? 'active' : ''}`}
              onClick={() => setShowPast((v) => !v)}
            >
              {showPast ? `Hide Past (${pastCount})` : `Show Past (${pastCount})`}
            </button>
          )}
          {withdrawnCount > 0 && (
            <button
              className={`btn btn-secondary ${showWithdrawn ? 'active' : ''}`}
              onClick={() => setShowWithdrawn((v) => !v)}
            >
              {showWithdrawn ? `Hide Withdrawn (${withdrawnCount})` : `Show Withdrawn (${withdrawnCount})`}
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {sortedIPOs.length === 0 ? (
        <div className="no-ipos">
          <TrendingUp size={48} />
          <p>No upcoming IPOs found</p>
          <button className="btn btn-secondary" onClick={handleRefresh}>
            Refresh Calendar
          </button>
        </div>
      ) : (
        <div className="ipo-table-wrapper">
          <table className="ipo-table">
            <thead>
              <tr>
                <th>Date</th>
                <th></th>
                <th>Company</th>
                <th>Exchange</th>
                <th>Price Range</th>
                <th>Shares</th>
                <th>Deal Size</th>
                <th>Debut</th>
                <th>Current</th>
                <th>Lock-up Expiry</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sortedIPOs.map((ipo) => (
                <tr
                  key={ipo.id}
                  className={
                    isWithdrawn(ipo) ? 'row--withdrawn' :
                    isPast(ipo) ? 'row--past' : ''
                  }
                >
                  <td className="col-date">{formatDate(ipo.date)}</td>
                  <td className="col-days">{formatDaysFromNow(ipo.date)}</td>
                  <td className="col-company">
                    <span className="company-name">{ipo.name}</span>
                    {ipo.symbol && (
                      <span className="company-symbol">{ipo.symbol}</span>
                    )}
                  </td>
                  <td className="col-exchange">{ipo.exchange ?? '—'}</td>
                  <td className="col-price">{formatPriceRange(ipo.price_range_low, ipo.price_range_high)}</td>
                  <td className="col-shares">{formatShares(ipo.shares)}</td>
                  <td className="col-deal">{formatDealSize(ipo.total_shares_value)}</td>
                  <td className="col-price">
                    {ipo.debut_price != null ? `$${ipo.debut_price.toFixed(2)}` : '—'}
                  </td>
                  <td className="col-price">
                    {ipo.current_price != null ? (
                      <span className="current-price-cell">
                        <span>${ipo.current_price.toFixed(2)}</span>
                        {ipo.debut_price != null && (
                          <span className={`price-change ${ipo.current_price >= ipo.debut_price ? 'up' : 'down'}`}>
                            {ipo.current_price >= ipo.debut_price ? '+' : ''}
                            {(((ipo.current_price - ipo.debut_price) / ipo.debut_price) * 100).toFixed(1)}%
                          </span>
                        )}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="col-date">
                    {isPast(ipo) && !isWithdrawn(ipo)
                      ? formatLockupExpiry(ipo.date)
                      : '—'}
                  </td>
                  <td className="col-status">
                    {ipo.status && (
                      <span className={`ipo-status ipo-status--${ipo.status.toLowerCase()}`}>
                        {ipo.status}
                      </span>
                    )}
                  </td>
                  <td className="col-watch">
                    {!isWithdrawn(ipo) && !watchedIds.has(ipo.id) && (
                      <button
                        className="watch-btn"
                        onClick={() => handleWatch(ipo)}
                        title="Add to watchlist"
                      >
                        <BookmarkPlus size={14} />
                      </button>
                    )}
                    {watchedIds.has(ipo.id) && (
                      <span className="watch-btn--added" title="Added to watchlist">✓</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default IPOCalendar;
