import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { RefreshCw, ArrowLeft, Edit2, Trash2, Bell } from 'lucide-react';
import { getCompany, deleteCompany, triggerSync, getCompanySyncs, getSync } from '../../api/client';
import type { Company, Sync } from '../../types';
import StockDataPanel from './StockDataPanel';
import AiAnalysisPanel from './AiAnalysisPanel';
import NewsFeed from './NewsFeed';
import SyncHistory from './SyncHistory';
import AnalystRatings from './AnalystRatings';
import EarningsCalendar from './EarningsCalendar';
import InsiderTransactions from './InsiderTransactions';
import StalenessAlert from '../shared/StalenessAlert';
import SentimentBadge from '../shared/SentimentBadge';
import TagChip from '../shared/TagChip';
import SentimentSparkline from './SentimentSparkline';
import AddCompanyModal from './AddCompanyModal';
import './CompanyDetail.css';

function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [company, setCompany] = useState<Company | null>(null);
  const [syncs, setSyncs] = useState<Sync[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    if (!id) return;

    try {
      const [companyData, syncsData] = await Promise.all([
        getCompany(id),
        getCompanySyncs(id),
      ]);
      setCompany(companyData);
      setSyncs(syncsData);
    } catch (error) {
      console.error('Failed to load company:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!id) return;

    setSyncing(true);
    try {
      const pendingSync = await triggerSync(id);

      // Poll until the background sync finishes (status leaves "syncing")
      let sync = pendingSync;
      while (sync.status === 'syncing') {
        await new Promise((res) => setTimeout(res, 2000));
        sync = await getSync(sync.id);
      }

      await loadData();
    } catch (error) {
      console.error('Sync failed:', error);
      alert('Sync failed. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !company) return;

    if (!confirm(`Are you sure you want to delete ${company.name}?`)) return;

    try {
      await deleteCompany(id);
      navigate('/');
    } catch (error) {
      console.error('Failed to delete company:', error);
      alert('Failed to delete company');
    }
  };

  const handleEditSuccess = () => {
    setShowEditModal(false);
    loadData();
  };

  if (loading) {
    return (
      <div className="company-detail">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="company-detail">
        <div className="error">Company not found</div>
      </div>
    );
  }

  const latestSync = syncs[0];
  const currentPrice = latestSync?.stock_price ?? null;
  const alertAboveTriggered = company.alert_above != null && currentPrice != null && currentPrice >= company.alert_above;
  const alertBelowTriggered = company.alert_below != null && currentPrice != null && currentPrice <= company.alert_below;

  return (
    <>
      <div className="company-detail">
        <button className="back-button" onClick={() => navigate('/')}>
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>

        {alertAboveTriggered && (
          <div className="alert-banner alert-banner--above">
            <Bell size={16} />
            Price alert: <strong>${currentPrice!.toFixed(2)}</strong> is above your alert of <strong>${company.alert_above!.toFixed(2)}</strong>
          </div>
        )}
        {alertBelowTriggered && (
          <div className="alert-banner alert-banner--below">
            <Bell size={16} />
            Price alert: <strong>${currentPrice!.toFixed(2)}</strong> is below your alert of <strong>${company.alert_below!.toFixed(2)}</strong>
          </div>
        )}

        <StalenessAlert sync={latestSync} />

        <div className="company-header">
          <div className="company-header-main">
            <div>
              <h1 className="company-name">{company.name}</h1>
              {company.ticker && <div className="company-ticker">{company.ticker}</div>}
              {company.website && (
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="company-website"
                >
                  {company.website}
                </a>
              )}
            </div>

            <div className="company-header-actions">
              <button
                className="btn btn-primary"
                onClick={handleSync}
                disabled={syncing}
              >
                <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
                {syncing ? 'Syncing...' : 'Sync Now'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowEditModal(true)}
              >
                <Edit2 size={16} />
                Edit
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                <Trash2 size={16} />
                Delete
              </button>
            </div>
          </div>

          <div className="company-meta">
            <div className="company-status">
              Status: <span className={`status-badge status-${company.status}`}>
                {company.status.replace('_', '-')}
              </span>
            </div>

            {company.industry && (
              <div className="company-industry">{company.industry}</div>
            )}

            {latestSync?.ai_sentiment && (
              <SentimentBadge sentiment={latestSync.ai_sentiment} />
            )}

            <SentimentSparkline syncs={syncs} />

            {company.tags.length > 0 && (
              <div className="company-tags">
                {company.tags.map((tag) => (
                  <TagChip key={tag.id} tag={tag} />
                ))}
              </div>
            )}
          </div>

          {company.description && (
            <div className="company-description">{company.description}</div>
          )}
        </div>

        {latestSync && (latestSync.ai_summary || latestSync.ai_sentiment) && (
          <AiAnalysisPanel
            sync={latestSync}
            companyName={company.name}
            ticker={company.ticker}
            status={company.status}
          />
        )}

        {company.status === 'public' && latestSync && (
          <StockDataPanel sync={latestSync} ticker={company.ticker} />
        )}

        {latestSync?.analyst_ratings && (
          <AnalystRatings ratings={latestSync.analyst_ratings} />
        )}

        {latestSync?.earnings_dates && latestSync.earnings_dates.length > 0 && (
          <EarningsCalendar earnings={latestSync.earnings_dates} />
        )}

        {latestSync?.insider_transactions && latestSync.insider_transactions.length > 0 && (
          <InsiderTransactions transactions={latestSync.insider_transactions} />
        )}

        {latestSync?.raw_news && latestSync.raw_news.length > 0 && (
          <NewsFeed articles={latestSync.raw_news} />
        )}

        {syncs.length > 0 && <SyncHistory syncs={syncs} />}

        {syncs.length === 0 && (
          <div className="no-syncs">
            <p>No sync history yet. Click "Sync Now" to fetch data.</p>
          </div>
        )}
      </div>

      {showEditModal && (
        <AddCompanyModal
          company={company}
          onClose={() => setShowEditModal(false)}
          onSuccess={handleEditSuccess}
        />
      )}
    </>
  );
}

export default CompanyDetail;
