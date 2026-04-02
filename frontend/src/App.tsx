import { BrowserRouter, Routes, Route } from 'react-router-dom';
import NavSidebar from './components/NavSidebar';
import AIChatPanel from './components/Sidebar';
import SearchPage from './pages/Search';
import AnalyzePage from './pages/Analyze';
import DiffPage from './pages/Diff';
import GlobalAudit from './pages/GlobalAudit';
import GraphNetwork from './pages/GraphNetwork';

function App() {
  return (
    <BrowserRouter>
      {/* Full-screen container */}
      <div className="relative flex h-screen w-screen overflow-hidden bg-background text-textMain">

        {/* Top floating nav — absolute positioned over content */}
        <NavSidebar />

        {/* Main content — takes full width, padded top so content doesn't hide under nav */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/analyze/:docId?" element={<AnalyzePage />} />
            <Route path="/diff" element={<DiffPage />} />
            <Route path="/audit" element={<GlobalAudit />} />
            <Route path="/graph" element={<GraphNetwork />} />
          </Routes>
        </div>

        {/* AI Chat Panel — right side */}
        <AIChatPanel />
      </div>
    </BrowserRouter>
  );
}

export default App;
