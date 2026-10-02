import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import HomePage from './components/home/HomePage';
import SettingsPage from './components/settings/SettingsPage';
import CompanyDetail from './components/company/CompanyDetail';
import IPOCalendar from './components/ipo/IPOCalendar';
import PortfolioPage from './components/portfolio/PortfolioPage';
import AnalyzePage from './components/analyze/AnalyzePage';
import NewsFeedPage from './components/news/NewsFeedPage';
import DiscoverPage from './components/discover/DiscoverPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="companies/:id" element={<CompanyDetail />} />
          <Route path="ipo-calendar" element={<IPOCalendar />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="analyze" element={<AnalyzePage />} />
          <Route path="news" element={<NewsFeedPage />} />
          <Route path="discover" element={<DiscoverPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
