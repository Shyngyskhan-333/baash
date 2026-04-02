import { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { getHeatmapData, getGraphHtmlUrl } from '../services/api';
import { Network, Activity } from 'lucide-react';
import { useStore } from '../store/useStore';

const GraphNetwork: React.FC = () => {
  const { graphState, setGraphState, activeScope } = useStore();
  const { activeTab, filterType, plotData, plotLayout } = graphState;
  const [heatmapError, setHeatmapError] = useState('');

  useEffect(() => {
    if (activeTab === 'heatmap' && (!plotData || plotData.length === 0)) {
      setHeatmapError('');
      getHeatmapData(activeScope)
        .then(data => {
          setGraphState({ 
            plotData: data.data || [], 
            plotLayout: data.layout || {} 
          });
        })
        .catch(() => {
          setHeatmapError('Тепловая карта недоступна — запустите аудит для построения графа (главная → Аудит O(N)).');
          setGraphState({ plotData: [] });
        });
    }
  }, [activeTab, plotData, setGraphState, activeScope]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#1a202c]">
      <header className="p-6 border-b border-[#2d3748] bg-surface flex items-center justify-between z-10 shrink-0">
        <div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-emerald-400 mb-1">Graph Analyzer & Heatmap</h1>
          <p className="text-sm text-textMuted">Визуализация коллизий и проблематичных участков.</p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Active Scope Badge in Header */}
          <div className="hidden md:flex items-center gap-2 bg-[#0d1117] border border-[#2d3748] px-3 py-1.5 rounded-lg">
             <span className="text-[10px] text-textMuted uppercase font-bold tracking-widest">Active Scope</span>
             <span className="bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded text-xs font-mono border border-indigo-500/30">
               {activeScope.length} Docs
             </span>
          </div>

          <div className="flex items-center gap-2 bg-[#0d1117] p-1 rounded-lg">
            <button
              onClick={() => setGraphState({ activeTab: 'graph' })}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition ${activeTab === 'graph' ? 'bg-indigo-600 text-white shadow' : 'text-textMuted hover:text-white'}`}
            >
              <Network size={16} /> Nodes Graph
            </button>
            <button
              onClick={() => setGraphState({ activeTab: 'heatmap' })}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition ${activeTab === 'heatmap' ? 'bg-indigo-600 text-white shadow' : 'text-textMuted hover:text-white'}`}
            >
              <Activity size={16} /> Heatmap
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 relative overflow-hidden flex flex-col">
        {activeTab === 'graph' && (
          <div className="flex-1 flex flex-col">
            <div className="p-4 bg-surface border-b border-[#2d3748] flex gap-4 items-center shrink-0">
              <span className="text-sm text-textMuted">Фильтр связей:</span>
              <select
                value={filterType}
                onChange={(e) => setGraphState({ filterType: e.target.value })}
                className="bg-[#0d1117] border border-[#2d3748] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-indigo-500 text-textMain"
              >
                <option value="Все">Все</option>
                <option value="Противоречия">Противоречия</option>
                <option value="Дубли">Дубли</option>
                <option value="Устаревшие">Устаревшие</option>
              </select>
              <div className="ml-auto text-xs text-textMuted bg-[#0d1117] px-3 py-1.5 rounded">
                Легенда: 🔴 Противоречие | 🔵 Дубль/Повтор | 🟡 Устаревшая норма
              </div>
            </div>
            {/* PyVis Network rendered inside iframe */}
            <iframe
              key={`${filterType}-${activeScope.join(',')}`}
              src={getGraphHtmlUrl(filterType, activeScope)}
              className="flex-1 w-full bg-white"
              title="Knowledge Graph"
            />
          </div>
        )}

        {activeTab === 'heatmap' && (
          <div className="flex-1 p-8 overflow-auto">
            <div className="max-w-6xl mx-auto bg-surface p-6 rounded-xl border border-[#2d3748] shadow-lg">
              <h2 className="text-lg font-medium text-emerald-300 mb-6">Тепловая карта структурных проблем</h2>
              {heatmapError ? (
                <div className="flex items-center justify-center h-64 text-yellow-400 text-sm">{heatmapError}</div>
              ) : plotData ? (
                <div className="w-full h-[600px] bg-white rounded overflow-hidden">
                  <Plot
                    data={plotData}
                    layout={{
                      ...plotLayout,
                      autosize: true,
                      margin: { t: 50, l: 200 },
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                    }}
                    useResizeHandler={true}
                    style={{ width: '100%', height: '100%' }}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-64 text-textMuted">
                  Загрузка тепловой карты...
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphNetwork;
