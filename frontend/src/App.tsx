import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import NavSidebar from './components/NavSidebar';
import AIChatPanel from './components/Sidebar';

const SearchPage = lazy(() => import('./pages/Search'));
const AnalyzePage = lazy(() => import('./pages/Analyze'));
const DiffPage = lazy(() => import('./pages/Diff'));
const GlobalAudit = lazy(() => import('./pages/GlobalAudit'));
const GraphNetwork = lazy(() => import('./pages/GraphNetwork'));
const SettingsPage = lazy(() => import('./pages/Settings'));

function PageFallback() {
  return (
    <div className="flex-1 flex items-center justify-center bg-background text-textMuted font-mono text-sm">
      Загрузка страницы...
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="relative flex h-screen w-screen overflow-hidden bg-background text-textMain">
        <NavSidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/analyze/:docId?" element={<AnalyzePage />} />
              <Route path="/diff" element={<DiffPage />} />
              <Route path="/audit" element={<GlobalAudit />} />
              <Route path="/graph" element={<GraphNetwork />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </Suspense>
        </div>
        <AIChatPanel />
      </div>
    </BrowserRouter>
  );
}

export default App;