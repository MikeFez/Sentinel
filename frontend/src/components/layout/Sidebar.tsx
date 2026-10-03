import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Newspaper, CalendarDays, Telescope, Settings, Plus, Search,
  ChevronDown, ChevronRight, Loader2, AlertTriangle, Bell, Clock, Target,
} from 'lucide-react';
import { useAppData } from '../../state/useAppData';
import { triggeredAlert, livePrice } from '../../lib/prices';
import type { CompanyWithSync } from '../../types';
import { pct, direction } from '../../lib/format';
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

function CompanyRow({ company }: { company: CompanyWithSync }) {
  const live = livePrice(company);
  const price = live?.price;
  const change = live?.change;
  const alert = triggeredAlert(company);
  return (
    <NavLink to={`/companies/${company.id}`} className="sb-company">
      <div className="sb-company-name">
        <span className="sb-name">{company.name}</span>
        {company.ticker && <span className="sb-ticker">{company.ticker}</span>}
      </div>
      <div className="sb-company-right">
        {company.is_syncing ? (
          <Loader2 size={12} className="spinning sb-icon-muted" aria-label="Syncing" />
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
  const { companies, tags, refresh } = useAppData();
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);

  const q = query.trim().toLowerCase();
  const visible = companies
    .filter((c) => !q || c.name.toLowerCase().includes(q) || c.ticker?.toLowerCase().includes(q))
    .sort((a, b) => a.name.localeCompare(b.name));

  const groups = tags
    .map((tag) => ({ id: tag.id, name: tag.name, color: tag.color, items: visible.filter((c) => c.tags.some((t) => t.id === tag.id)) }))
    .filter((g) => g.items.length > 0);
  const untagged = visible.filter((c) => c.tags.length === 0);
  if (untagged.length) groups.push({ id: 'untagged', name: groups.length ? 'Other' : 'Companies', color: '', items: untagged });

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
            </NavLink>
          ))}
        </nav>

        <div className="sb-section-head">
          <span>Companies</span>
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
          {companies.length === 0 && (
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
              {!collapsed.has(g.id) && g.items.map((c) => <CompanyRow key={c.id} company={c} />)}
            </div>
          ))}
          {q && visible.length === 0 && <div className="sb-none">No matches</div>}
        </div>

        <NavLink to="/settings" className="sb-nav-item sb-settings">
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
