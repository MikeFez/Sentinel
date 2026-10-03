import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { getNewsFeed, type NewsFeedArticle } from '../../api/client';
import { ago, parseTime } from '../../lib/format';
import '../news/NewsFeedPage.css';

/** Every stored article for one company, newest first (not just the latest sync's). */
function CompanyNews({ companyId, refreshKey }: { companyId: string; refreshKey: string }) {
  const [articles, setArticles] = useState<NewsFeedArticle[] | null>(null);

  useEffect(() => {
    getNewsFeed(200, companyId).then(setArticles).catch(() => setArticles([]));
  }, [companyId, refreshKey]);

  if (articles === null) return <div className="muted">Loading…</div>;
  if (!articles.length) return <div className="card muted">No news stored yet.</div>;
  return (
    <div className="news-list">
      {articles.map((a) => (
        <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer" className="news-item">
          <div className="news-meta">
            {a.source && <span className="news-source">{a.source}</span>}
            <span className="news-date" title={a.published_at ? parseTime(a.published_at).toLocaleString() : undefined}>
              {a.published_at ? ago(a.published_at) : ''}
            </span>
          </div>
          <div className="news-title">{a.title}<ExternalLink size={12} className="news-external-icon" /></div>
          {a.summary && <div className="news-summary">{a.summary}</div>}
        </a>
      ))}
    </div>
  );
}

export default CompanyNews;
