import { useEffect, useMemo, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { getNewsFeed, type NewsFeedArticle } from '../../api/client';
import { ago, parseTime } from '../../lib/format';
import './NewsFeedPage.css';

const LAST_VISIT_KEY = 'sentinel.news.lastVisit';

function readLastVisit(): number {
  try {
    return Number(localStorage.getItem(LAST_VISIT_KEY)) || 0;
  } catch {
    return 0;
  }
}

function NewsFeedPage() {
  const [articles, setArticles] = useState<NewsFeedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [company, setCompany] = useState<string | null>(null);
  // Articles first seen after the previous visit are marked new (per browser)
  const [lastVisit] = useState(readLastVisit);

  useEffect(() => {
    getNewsFeed(300)
      .then(setArticles)
      .catch((err) => console.error('Failed to load news:', err))
      .finally(() => setLoading(false));
    return () => {
      try {
        localStorage.setItem(LAST_VISIT_KEY, String(Date.now()));
      } catch {
        /* private mode: everything just stays "not new" */
      }
    };
  }, []);

  const companies = useMemo(() => {
    const counts = new Map<string, { id: string; name: string; count: number }>();
    for (const a of articles) {
      const c = counts.get(a.company_id) ?? { id: a.company_id, name: a.company_name, count: 0 };
      c.count++;
      counts.set(a.company_id, c);
    }
    return [...counts.values()].sort((a, b) => b.count - a.count);
  }, [articles]);

  const isNew = (a: NewsFeedArticle) => lastVisit > 0 && parseTime(a.first_seen_at).getTime() > lastVisit;
  const q = query.trim().toLowerCase();
  const shown = articles.filter(
    (a) => (!company || a.company_id === company) && (!q || a.title.toLowerCase().includes(q) || a.summary.toLowerCase().includes(q)),
  );
  const newCount = articles.filter(isNew).length;

  return (
    <div className="news-feed-page">
      <div className="news-header">
        <div className="news-header-content">
          <div>
            <h1>News</h1>
            <p className="news-subtitle">
              {articles.length} articles from {companies.length} {companies.length === 1 ? 'company' : 'companies'}
              {newCount > 0 && <> · <span className="news-new-count">{newCount} new since your last visit</span></>}
            </p>
          </div>
        </div>
        <input className="news-filter" type="search" placeholder="Search headlines…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {companies.length > 1 && (
        <div className="news-chips" role="group" aria-label="Filter by company">
          <button className={`news-chip ${company === null ? 'active' : ''}`} onClick={() => setCompany(null)}>All</button>
          {companies.map((c) => (
            <button key={c.id} className={`news-chip ${company === c.id ? 'active' : ''}`} onClick={() => setCompany(company === c.id ? null : c.id)}>
              {c.name} <span className="muted">{c.count}</span>
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="muted">Loading…</div>
      ) : articles.length === 0 ? (
        <div className="news-empty"><p>No news yet. Sync your companies to fetch their latest news.</p></div>
      ) : (
        <div className="news-list">
          {shown.map((article) => (
            <a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" className="news-item">
              <div className="news-meta">
                {isNew(article) && <span className="news-new">New</span>}
                <span className="news-company">{article.company_name}</span>
                {article.company_ticker && <span className="news-ticker">{article.company_ticker}</span>}
                {article.source && <span className="news-source">{article.source}</span>}
                <span className="news-date" title={article.published_at ? parseTime(article.published_at).toLocaleString() : undefined}>
                  {article.published_at ? ago(article.published_at) : ''}
                </span>
              </div>
              <div className="news-title">
                {article.title}
                <ExternalLink size={12} className="news-external-icon" />
              </div>
              {article.summary && <div className="news-summary">{article.summary}</div>}
            </a>
          ))}
          {shown.length === 0 && <div className="news-no-results">No articles match.</div>}
        </div>
      )}
    </div>
  );
}

export default NewsFeedPage;
