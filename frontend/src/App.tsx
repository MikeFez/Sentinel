import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppDataProvider } from './state/AppData';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './components/dashboard/DashboardPage';
import SettingsPage from './components/settings/SettingsPage';
import CompanyDetail from './components/company/CompanyDetail';
import IPOCalendar from './components/ipo/IPOCalendar';
import NewsFeedPage from './components/news/NewsFeedPage';
import ResearchPage from './components/research/ResearchPage';
import ScorecardPage from './components/scorecard/ScorecardPage';

function App() {
  return (
    <AppDataProvider>
      <Router>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="companies/:id" element={<CompanyDetail />} />
            <Route path="news" element={<NewsFeedPage />} />
            <Route path="ipo-calendar" element={<IPOCalendar />} />
            <Route path="research" element={<ResearchPage />} />
            <Route path="scorecard" element={<ScorecardPage />} />
            <Route path="settings" element={<SettingsPage />} />
            {/* Pages that were merged into others */}
            <Route path="portfolio" element={<Navigate to="/" replace />} />
            <Route path="analyze" element={<Navigate to="/research?tab=analyze" replace />} />
            <Route path="discover" element={<Navigate to="/research?tab=discover" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </AppDataProvider>
  );
}

export default App;
