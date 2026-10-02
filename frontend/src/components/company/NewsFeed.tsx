import { ExternalLink } from 'lucide-react';
import type { NewsArticle } from '../../types';
import './NewsFeed.css';

interface NewsFeedProps {
  articles: NewsArticle[];
}

function NewsFeed({ articles }: NewsFeedProps) {
  const formatDate = (timestamp: number) => {
    if (!timestamp) return '';

    try {
      // Finnhub returns Unix timestamp in seconds
      const date = new Date(timestamp * 1000);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffHours < 1) return 'Less than an hour ago';
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return '1 day ago';
      if (diffDays < 7) return `${diffDays} days ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="news-feed">
      <h2 className="section-title">Recent News</h2>

      <div className="news-list">
        {articles.map((article, index) => (
          <a
            key={index}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="news-item"
          >
            <div className="news-header">
              <h3 className="news-title">{article.title}</h3>
              <ExternalLink size={16} className="news-icon" />
            </div>
            <div className="news-meta">
              {article.source && (
                <span className="news-source">{article.source}</span>
              )}
              {article.published_at && (
                <span className="news-date">{formatDate(article.published_at)}</span>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export default NewsFeed;
