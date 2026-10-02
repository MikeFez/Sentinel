import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Home, Plus, Search, Settings, ChevronDown, ChevronRight, Calendar, Bell, Loader, Briefcase, Sparkles, Newspaper, Telescope } from 'lucide-react';
import { getCompanies, getTags } from '../../api/client';
import type { CompanyWithSync, Tag } from '../../types';
import AddCompanyModal from '../company/AddCompanyModal';
import './Sidebar.css';

function Sidebar() {
  const [companies, setCompanies] = useState<CompanyWithSync[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTags, setExpandedTags] = useState<Set<string>>(new Set());
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [companiesData, tagsData] = await Promise.all([
        getCompanies(),
        getTags(),
      ]);
      setCompanies(companiesData);
      setTags(tagsData);
      // Expand all tags by default
      setExpandedTags(new Set(tagsData.map((tag) => tag.id)));
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTag = (tagId: string) => {
    const newExpanded = new Set(expandedTags);
    if (newExpanded.has(tagId)) {
      newExpanded.delete(tagId);
    } else {
      newExpanded.add(tagId);
    }
    setExpandedTags(newExpanded);
  };

  const getCompanyStatusDot = (status: string) => {
    const colors = {
      public: 'var(--status-public)',
      pre_ipo: 'var(--status-pre-ipo)',
      private: 'var(--status-private)',
      acquired: 'var(--status-acquired)',
    };
    return colors[status as keyof typeof colors] || 'var(--text-muted)';
  };

  const filteredCompanies = companies.filter((company) =>
    company.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    company.ticker?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group companies by tags
  const companiesByTag: Record<string, CompanyWithSync[]> = {};
  const untaggedCompanies: CompanyWithSync[] = [];

  filteredCompanies.forEach((company) => {
    if (company.tags.length === 0) {
      untaggedCompanies.push(company);
    } else {
      company.tags.forEach((tag) => {
        if (!companiesByTag[tag.id]) {
          companiesByTag[tag.id] = [];
        }
        companiesByTag[tag.id].push(company);
      });
    }
  });

  const handleCompanyAdded = () => {
    loadData();
    setShowAddModal(false);
  };

  if (loading) {
    return (
      <aside className="sidebar">
        <div className="sidebar-loading">Loading...</div>
      </aside>
    );
  }

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-title">Sentinel</h1>
          <button
            className="icon-button"
            onClick={() => navigate('/settings')}
            title="Settings"
          >
            <Settings size={18} />
          </button>
        </div>

        <Link to="/" className="sidebar-home-button">
          <Home size={18} />
          <span>Home</span>
        </Link>

        <Link to="/ipo-calendar" className="sidebar-home-button">
          <Calendar size={18} />
          <span>IPO Calendar</span>
        </Link>

        <Link to="/news" className="sidebar-home-button">
          <Newspaper size={18} />
          <span>News Feed</span>
        </Link>

        <Link to="/portfolio" className="sidebar-home-button">
          <Briefcase size={18} />
          <span>Portfolio</span>
        </Link>

        <Link to="/analyze" className="sidebar-home-button">
          <Sparkles size={18} />
          <span>Analyze</span>
        </Link>

        <Link to="/discover" className="sidebar-home-button">
          <Telescope size={18} />
          <span>Discover</span>
        </Link>

        <div className="sidebar-search">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search companies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="sidebar-companies">
          {tags.map((tag) => {
            const tagCompanies = companiesByTag[tag.id] || [];
            if (tagCompanies.length === 0) return null;

            const isExpanded = expandedTags.has(tag.id);

            return (
              <div key={tag.id} className="tag-group">
                <button
                  className="tag-header"
                  onClick={() => toggleTag(tag.id)}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span
                    className="tag-dot"
                    style={{ backgroundColor: tag.color }}
                  />
                  <span className="tag-name">{tag.name}</span>
                  <span className="tag-count">{tagCompanies.length}</span>
                </button>
                {isExpanded && (
                  <div className="tag-companies">
                    {tagCompanies.map((company) => (
                      <Link
                        key={company.id}
                        to={`/companies/${company.id}`}
                        className="company-item"
                      >
                        <span
                          className="status-dot"
                          style={{ backgroundColor: getCompanyStatusDot(company.status) }}
                        />
                        <div className="company-info">
                          <div className="company-name">{company.name}</div>
                          {company.ticker && (
                            <div className="company-ticker">{company.ticker}</div>
                          )}
                        </div>
                        <div className="company-indicators">
                          {company.is_syncing && <Loader size={10} className="indicator-syncing" />}
                          {!company.is_syncing && company.is_stale && <span className="indicator-stale" title="Data is stale" />}
                          {company.has_alert && <Bell size={10} className="indicator-alert" />}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {untaggedCompanies.length > 0 && (
            <div className="tag-group">
              <button
                className="tag-header"
                onClick={() => toggleTag('untagged')}
              >
                {expandedTags.has('untagged') ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                <span className="tag-name">Untagged</span>
                <span className="tag-count">{untaggedCompanies.length}</span>
              </button>
              {expandedTags.has('untagged') && (
                <div className="tag-companies">
                  {untaggedCompanies.map((company) => (
                    <Link
                      key={company.id}
                      to={`/companies/${company.id}`}
                      className="company-item"
                    >
                      <span
                        className="status-dot"
                        style={{ backgroundColor: getCompanyStatusDot(company.status) }}
                      />
                      <div className="company-info">
                        <div className="company-name">{company.name}</div>
                        {company.ticker && (
                          <div className="company-ticker">{company.ticker}</div>
                        )}
                      </div>
                      <div className="company-indicators">
                        {company.is_syncing && <Loader size={10} className="indicator-syncing" />}
                        {!company.is_syncing && company.is_stale && <span className="indicator-stale" title="Data is stale" />}
                        {company.has_alert && <Bell size={10} className="indicator-alert" />}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <button
          className="add-company-button"
          onClick={() => setShowAddModal(true)}
        >
          <Plus size={18} />
          <span>Add Company</span>
        </button>
      </aside>

      {showAddModal && (
        <AddCompanyModal
          onClose={() => setShowAddModal(false)}
          onSuccess={handleCompanyAdded}
        />
      )}
    </>
  );
}

export default Sidebar;
