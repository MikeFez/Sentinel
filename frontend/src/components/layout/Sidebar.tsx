import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Newspaper, CalendarDays, Telescope, Settings, Plus, Search,
  ChevronDown, ChevronRight, Loader2, AlertTriangle, Bell, Clock, Target, Activity,
} from 'lucide-react';
import { useAppData } from '../../state/useAppData';
import { triggeredAlert, livePrice } from '../../lib/prices';
import type { CompanyWithSync } from '../../types';
import { pct, direction } from '../../lib/format';
import { hasUnreadNews } from '../../lib/newsSeen';
import { syncStepText } from '../../lib/syncSteps';
import AddCompanyModal from '../company/AddCompanyModal';
import './Sidebar.css';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/news', label: 'News', icon: Newspaper },
  { to: '/ipo-calendar', label: 'IPOs', icon: CalendarDays },
  { to: '/research', label: 'Research', icon: Telescope },
  { to: '/scorecard', label: 'Scorecard', icon: Target },
];

const STATUS_LABEL: Record<string, string> = { private: 'Private', pre_ipo: 'Pre-IPO', acquired: 'Acquired' };

type GroupBy = 'portfolio' | 'tags';
const GROUP_KEY = 'sentinel.sidebar.groupBy';

function readGroupBy(): GroupBy {
  try {
    return localStorage.getItem(GROUP_KEY) === 'tags' ? 'tags' : 'portfolio';
  } catch {
    return 'portfolio';
  }
}

function CompanyRow({ company, unread, showTags }: { company: CompanyWithSync; unread: boolean; showTags: boolean }) {
  const live = livePrice(company);
  const price = live?.price;
  const change = live?.change;
  const alert = triggeredAlert(company);
  return (
    <NavLink to={`/companies/${company.id}`} className="sb-company">
      {unread && <span className="sb-unread" title="New news since you last looked" aria-label="New news" />}
      <div className="sb-company-name">
        <span className="sb-name">{company.name}</span>
        {company.ticker && <span className="sb-ticker">{company.ticker}</span>}
        {showTags && company.tags.map((t) => <span key={t.id} className="sb-row-tag" style={{ backgroundColor: t.color }} title={t.name} />)}
      </div>
      <div className="sb-company-right">
        {company.is_syncing ? (
          <span title={syncStepText(company)} className="sb-icon-wrap"><Loader2 size={12} className="spinning sb-icon-muted" aria-label="Syncing" /></span>
        ) : company.sync_error ? (
          <AlertTriangle size={12} className="sb-icon-error" aria-label="Last sync failed" />
        ) : company.is_stale ? (
          <Clock size={12} className="sb-icon-muted" aria-label="Data is stale" />
        ) : null}
        {alert && <Bell size={12} className="sb-icon-alert" aria-label="Price alert triggered" />}
        {price != null ? (
          <span className={`sb-change ${direction(change)}`}>{pct(change)}</span>
        ) : (
          <span className="sb-status">{STATUS_LABEL[company.status] ?? ''}</span>
        )}
      </div>
    </NavLink>
  );
}

function Sidebar({ open = false }: { open?: boolean }) {
  const { companies, tags, loaded, refresh, newsSeen } = useAppData();
  const unread = (c: CompanyWithSync) => hasUnreadNews(c.latest_news_at, newsSeen.lastVisit, newsSeen.byCompany[c.id]);
  const anyUnread = companies.some(unread);
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);
  // Portfolio / watchlist comes from shares owned (as on the dashboard); tags are an alternative view
  const [groupBy, setGroupBy] = useState<GroupBy>(readGroupBy);
  const changeGroupBy = (g: GroupBy) => {
    setGroupBy(g);
    try {
      localStorage.setItem(GROUP_KEY, g);
    } catch {
      /* not remembered */
    }
  };

  const q = query.trim().toLowerCase();
  const visible = companies
    .filter((c) => !q || c.name.toLowerCase().includes(q) || c.ticker?.toLowerCase().includes(q))
    .sort((a, b) => a.name.localeCompare(b.name));

  const owned = (c: CompanyWithSync) => (c.shares_owned ?? 0) > 0;
  let groups: { id: string; name: string; color: string; items: CompanyWithSync[] }[];
  if (groupBy === 'portfolio') {
    groups = [
      { id: 'portfolio', name: 'Portfolio', color: '', items: visible.filter(owned) },
      { id: 'watchlist', name: 'Watchlist', color: '', items: visible.filter((c) => !owned(c)) },
    ].filter((g) => g.items.length > 0);
  } else {
    groups = tags
      .map((tag) => ({ id: tag.id, name: tag.name, color: tag.color, items: visible.filter((c) => c.tags.some((t) => t.id === tag.id)) }))
      .filter((g) => g.items.length > 0);
    const untagged = visible.filter((c) => c.tags.length === 0);
    if (untagged.length) groups.push({ id: 'untagged', name: groups.length ? 'Other' : 'Companies', color: '', items: untagged });
  }

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <>
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sb-brand">Sentinel</div>

        <nav className="sb-nav">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="sb-nav-item">
              <Icon size={16} />
              <span>{label}</span>
              {to === '/news' && anyUnread && <span className="sb-nav-dot" aria-label="New news" />}
            </NavLink>
          ))}
        </nav>

        <div className="sb-section-head">
          <span>Companies</span>
          {tags.length > 0 && (
            <div className="sb-groupby" role="radiogroup" aria-label="Group companies by">
              <button role="radio" aria-checked={groupBy === 'portfolio'} className={groupBy === 'portfolio' ? 'active' : ''} onClick={() => changeGroupBy('portfolio')}>Holdings</button>
              <button role="radio" aria-checked={groupBy === 'tags'} className={groupBy === 'tags' ? 'active' : ''} onClick={() => changeGroupBy('tags')}>Tags</button>
            </div>
          )}
          <button className="sb-add" onClick={() => setShowAdd(true)} title="Add company" aria-label="Add company">
            <Plus size={15} />
          </button>
        </div>

        {companies.length > 5 && (
          <div className="sb-search">
            <Search size={14} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter" aria-label="Filter companies" />
          </div>
        )}

        <div className="sb-companies">
          {loaded && companies.length === 0 && (
            <button className="sb-empty" onClick={() => setShowAdd(true)}>
              <Plus size={14} /> Add your first company
            </button>
          )}
          {groups.map((g) => (
            <div key={g.id} className="sb-group">
              <button className="sb-group-head" onClick={() => toggle(g.id)}>
                {collapsed.has(g.id) ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                {g.color && <span className="sb-tag-dot" style={{ backgroundColor: g.color }} />}
                <span className="sb-group-name">{g.name}</span>
                <span className="sb-group-count">{g.items.length}</span>
              </button>
              {!collapsed.has(g.id) && g.items.map((c) => <CompanyRow key={c.id} company={c} unread={unread(c)} showTags={groupBy === 'portfolio'} />)}
            </div>
          ))}
          {q && visible.length === 0 && <div className="sb-none">No matches</div>}
        </div>

        <NavLink to="/activity" className="sb-nav-item sb-activity">
          <Activity size={16} />
          <span>Activity</span>
        </NavLink>
        <NavLink to="/settings" className="sb-nav-item">
          <Settings size={16} />
          <span>Settings</span>
        </NavLink>
      </aside>

      {showAdd && (
        <AddCompanyModal
          onClose={() => setShowAdd(false)}
          onSuccess={() => {
            setShowAdd(false);
            refresh();
          }}
        />
      )}
    </>
  );
}

export default Sidebar;
