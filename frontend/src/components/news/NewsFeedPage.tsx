import { useState, useEffect } from 'react';
import { Newspaper, ExternalLink } from 'lucide-react';
import { getNewsFeed, type NewsFeedArticle } from '../../api/client';
import './NewsFeedPage.css';

function NewsFeedPage() {
  const [articles, setArticles] = useState<NewsFeedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    loadFeed();
  }, []);

  const loadFeed = async () => {
    try {
      const data = await getNewsFeed(200);
      setArticles(data);
    } catch (error) {
      console.error('Failed to load news feed:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (ts: number) => {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    const now = Date.now();
    const diff = now - d.getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const filtered = filter
    ? articles.filter(
        (a) =>
          a.title.toLowerCase().includes(filter.toLowerCase()) ||
          a.company_name.toLowerCase().includes(filter.toLowerCase()) ||
          (a.company_ticker?.toLowerCase().includes(filter.toLowerCase()) ?? false)
      )
    : articles;

  // Group by company for a cleaner scan
  const companies = Array.from(new Set(articles.map((a) => a.company_name)));

  if (loading) {
    return (
      <div className="news-feed-page">
        <div className="loading">Loading news feed...</div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="news-feed-page">
        <div className="news-header">
          <Newspaper size={32} className="news-icon" />
          <div>
            <h1>News Feed</h1>
            <p className="news-subtitle">Latest news across all tracked companies</p>
          </div>
        </div>
        <div className="news-empty">
          <Newspaper size={48} />
          <p>No news yet</p>
          <p className="news-empty-hint">Sync your companies to fetch their latest news.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="news-feed-page">
      <div className="news-header">
        <div className="news-header-content">
          <Newspaper size={32} className="news-icon" />
          <div>
            <h1>News Feed</h1>
            <p className="news-subtitle">
              {articles.length} articles from {companies.length} companies
            </p>
          </div>
        </div>
        <input
          className="news-filter"
          type="text"
          placeholder="Filter by company or keyword…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="news-list">
        {filtered.map((article, i) => (
          <a
            key={`${article.company_id}-${i}`}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="news-item"
          >
            <div className="news-meta">
              <span className="news-company">{article.company_name}</span>
              {article.company_ticker && (
                <span className="news-ticker">{article.company_ticker}</span>
              )}
              {article.source && (
                <span className="news-source">{article.source}</span>
              )}
              <span className="news-date">{formatDate(article.published_at)}</span>
            </div>
            <div className="news-title">
              {article.title}
              <ExternalLink size={12} className="news-external-icon" />
            </div>
            {article.summary && (
              <div className="news-summary">{article.summary}</div>
            )}
          </a>
        ))}
        {filtered.length === 0 && (
          <div className="news-no-results">No articles match "{filter}"</div>
        )}
      </div>
    </div>
  );
}

export default NewsFeedPage;
