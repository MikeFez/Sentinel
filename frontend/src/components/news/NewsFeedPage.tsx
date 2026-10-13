import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ExternalLink, ChevronDown, ChevronRight } from 'lucide-react';
import { getNewsFeed, getStories, type NewsFeedArticle, type Story } from '../../api/client';
import { ago, parseTime } from '../../lib/format';
import { useAppData } from '../../state/useAppData';
import { useTitle } from '../../lib/useTitle';
import './NewsFeedPage.css';

function NewsFeedPage() {
  const [articles, setArticles] = useState<NewsFeedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  // Filters live in the URL, so reloads, Back and shared links keep them
  const [params, setParams] = useSearchParams();
  const query = params.get('q') ?? '';
  const company = params.get('company');
  const view = params.get('view') === 'articles' ? 'articles' : 'stories';
  const materialOnly = params.get('material') === '1';
  const setParam = (key: string, value: string | null) =>
    setParams((p) => {
      const next = new URLSearchParams(p);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    }, { replace: true });
  const setQuery = (v: string) => setParam('q', v || null);
  const setCompany = (v: string | null) => setParam('company', v);
  const setView = (v: 'stories' | 'articles') => setParam('view', v === 'articles' ? v : null);
  const setMaterialOnly = (v: boolean) => setParam('material', v ? '1' : null);
  const [stories, setStories] = useState<Story[]>([]);
  const [open, setOpen] = useState<Set<string>>(new Set());
  // Articles first seen after the previous visit are marked new (per browser)
  const { newsSeen, markNewsSeen } = useAppData();
  const [lastVisit] = useState(newsSeen.lastVisit);
  useTitle('News');

  useEffect(() => {
    getStories().then(setStories).catch(() => setStories([]));
    getNewsFeed(300)
      .then(setArticles)
      .catch((err) => console.error('Failed to load news:', err))
      .finally(() => setLoading(false));
    return () => markNewsSeen(null);
  }, [markNewsSeen]);

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
  const shownStories = stories.filter(
    (s) => (!company || s.company_id === company) && (!materialOnly || s.material) &&
      (!q || s.title.toLowerCase().includes(q) || s.articles.some((a) => a.title.toLowerCase().includes(q))),
  );
  const storyIsNew = (s: Story) => lastVisit > 0 && parseTime(s.last_seen_at).getTime() > lastVisit;
  const toggle = (id: string) => setOpen((o) => { const n = new Set(o); if (n.has(id)) n.delete(id); else n.add(id); return n; });

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

      <div className="news-viewbar">
        <div className="segmented" role="radiogroup" aria-label="View">
          <button role="radio" aria-checked={view === 'stories'} className={view === 'stories' ? 'active' : ''} onClick={() => setView('stories')}>Stories</button>
          <button role="radio" aria-checked={view === 'articles'} className={view === 'articles' ? 'active' : ''} onClick={() => setView('articles')}>All articles</button>
        </div>
        {view === 'stories' && (
          <label className="news-material-toggle">
            <input type="checkbox" checked={materialOnly} onChange={(e) => setMaterialOnly(e.target.checked)} /> Material only
          </label>
        )}
      </div>

      {view === 'stories' && !loading && (
        <div className="news-list">
          {shownStories.map((s) => (
            <div key={s.id} className="news-item story">
              <button className="story-head" onClick={() => toggle(s.id)} aria-expanded={open.has(s.id)}>
                <div className="news-meta">
                  {storyIsNew(s) && <span className="news-new">New</span>}
                  {s.material ? <span className="story-material">Material</span> : <span className="story-noise">Noise</span>}
                  <span className="news-company">{s.company_name}</span>
                  {s.themes.map((t) => <span key={t} className="story-theme">{t}</span>)}
                  <span className="news-date">{ago(s.last_seen_at)}</span>
                </div>
                <div className="news-title">
                  {open.has(s.id) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  {s.title}
                  <span className="muted story-count">{s.articles.length} {s.articles.length === 1 ? 'article' : 'articles'}</span>
                </div>
                {s.summary && <div className="news-summary">{s.summary}</div>}
              </button>
              {open.has(s.id) && (
                <ul className="story-articles">
                  {s.articles.map((a) => (
                    <li key={a.id}>
                      <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title} <ExternalLink size={11} /></a>
                      <span className="muted">{a.source}{a.published_at ? ` · ${ago(a.published_at)}` : ''}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {shownStories.length === 0 && (
            <div className="news-no-results">
              {stories.length ? 'No stories match.' : 'No stories yet. Articles are grouped into stories during each sync.'}
            </div>
          )}
        </div>
      )}

      {view === 'stories' ? null : loading ? (
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
