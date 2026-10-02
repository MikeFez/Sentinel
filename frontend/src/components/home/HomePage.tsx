import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { getCompanies, getHomeSummary, syncStaleCompanies, type HomeSummary } from '../../api/client';
import type { CompanyWithSync } from '../../types';
import RecentActivity from './RecentActivity';
import NeedsAttention from './NeedsAttention';
import OverviewCards from './OverviewCards';
import EarningsCountdown from './EarningsCountdown';
import './HomePage.css';

function HomePage() {
  const [companies, setCompanies] = useState<CompanyWithSync[]>([]);
  const [summary, setSummary] = useState<HomeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [bulkSyncing, setBulkSyncing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [companiesData, summaryData] = await Promise.all([
        getCompanies(),
        getHomeSummary(),
      ]);
      setCompanies(companiesData);
      setSummary(summaryData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkSync = async () => {
    setBulkSyncing(true);
    try {
      const result = await syncStaleCompanies();
      alert(result.message);
      await loadData();
    } catch (error) {
      console.error('Bulk sync failed:', error);
      alert('Failed to queue syncs');
    } finally {
      setBulkSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="home-page">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (companies.length === 0) {
    return (
      <div className="home-page">
        <div className="empty-state">
          <h2>Welcome to Sentinel</h2>
          <p>Get started by adding your first company to track.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <div className="home-header">
        <div>
          <h1>Dashboard</h1>
          <p className="home-subtitle">
            Tracking {summary?.total_companies || companies.length}{' '}
            {(summary?.total_companies || companies.length) === 1 ? 'company' : 'companies'}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleBulkSync}
          disabled={bulkSyncing}
        >
          <RefreshCw size={15} className={bulkSyncing ? 'spinning' : ''} />
          {bulkSyncing ? 'Queuing…' : 'Sync All Stale'}
        </button>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-main">
          {summary && <RecentActivity activity={summary.recent_activity} />}
          <OverviewCards companies={companies} />
        </div>

        <div className="dashboard-sidebar">
          {summary && <NeedsAttention staleCompanies={summary.stale_companies} />}
          {summary && summary.upcoming_earnings?.length > 0 && (
            <EarningsCountdown earnings={summary.upcoming_earnings} />
          )}
        </div>
      </div>
    </div>
  );
}

export default HomePage;
