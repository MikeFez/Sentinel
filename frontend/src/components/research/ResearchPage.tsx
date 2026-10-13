import { useSearchParams } from 'react-router-dom';
import AnalyzePage from '../analyze/AnalyzePage';
import DiscoverPage from '../discover/DiscoverPage';
import { useTitle } from '../../lib/useTitle';

const TABS = [
  { id: 'analyze', label: 'Analyze a company', blurb: 'A one-off AI read on any ticker or company, without tracking it.' },
  { id: 'discover', label: 'Discover by theme', blurb: 'Describe a theme or sector to find public companies in it, then analyze or track them.' },
] as const;

function ResearchPage() {
  useTitle('Research');
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.id === params.get('tab')) ?? TABS[0];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Research</h1>
          <p className="muted">{tab.blurb}</p>
        </div>
      </header>
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={t.id === tab.id} className={`tab ${t.id === tab.id ? 'active' : ''}`}
            onClick={() => setParams({ tab: t.id }, { replace: true })}>
            {t.label}
          </button>
        ))}
      </div>
      {/* Both stay mounted so switching tabs doesn't lose a running discovery or a result */}
      <div hidden={tab.id !== 'analyze'}><AnalyzePage /></div>
      <div hidden={tab.id !== 'discover'}><DiscoverPage /></div>
    </div>
  );
}

export default ResearchPage;
