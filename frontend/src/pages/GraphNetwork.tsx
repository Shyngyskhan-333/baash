import { useState, useEffect } from 'react';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';

import PlotlyImport from 'plotly.js-dist-min';
import plotlyFactory from 'react-plotly.js/factory';
import { getHeatmapData, getGraphHtmlUrl } from '../services/api';
import { Network, Activity, Info } from 'lucide-react';
import { useStore } from '../store/useStore';

type PlotProps = {
  data?: unknown;
  layout?: unknown;
  useResizeHandler?: boolean;
  style?: React.CSSProperties;
};

const Plotly = (PlotlyImport as { default?: unknown }).default ?? PlotlyImport;
const createPlotlyComponent =
  typeof plotlyFactory === 'function'
    ? plotlyFactory
    : (plotlyFactory as { default?: unknown }).default;
const Plot = (createPlotlyComponent as (plotly: unknown) => React.ComponentType<PlotProps>)(Plotly);

const GraphNetwork: React.FC = () => {
  const { graphState, setGraphState, activeScope } = useStore();
  const { activeTab, filterType, plotData, plotLayout } = graphState;
  const [heatmapError, setHeatmapError] = useState('');

  useEffect(() => {
    if (activeTab === 'heatmap') {
      getHeatmapData(activeScope)
        .then(data => {
          setHeatmapError('');
          setGraphState({ plotData: data.data || [], plotLayout: data.layout || {} });
        })
        .catch(err => {
          console.error('Heatmap fetch error:', err);
          setHeatmapError('Тепловая карта недоступна — запустите аудит для построения графа.');
          setGraphState({ plotData: [] });
        });
    }
  }, [activeTab, setGraphState, activeScope]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      <header className="px-8 py-5 border-b border-border bg-surface flex items-center justify-between z-10 shrink-0 mt-14">
        <div>
          <h1 className="text-xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-primaryStrong mb-0.5">
            Graph Analyzer
          </h1>
          <p className="text-xs text-textMuted">Визуализация коллизий и структурных связей.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 bg-surfaceAlt border border-border px-3 py-1.5 rounded-lg">
            <span className="text-[9px] text-textDim uppercase font-bold tracking-widest font-mono">Scope</span>
            <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs font-mono border border-primary/15">
              {activeScope.length || 'All'}
            </span>
          </div>

          <div className="flex items-center gap-1 bg-surfaceAlt p-1 rounded-lg border border-border">
            <button
              onClick={() => setGraphState({ activeTab: 'graph' })}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-sm font-medium transition ${
                activeTab === 'graph' ? 'bg-primary/10 text-primary border border-primary/15' : 'text-textMuted hover:text-textSub'
              }`}
            >
              <Network size={14} /> Граф
            </button>
            <button
              onClick={() => setGraphState({ activeTab: 'heatmap' })}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-sm font-medium transition ${
                activeTab === 'heatmap' ? 'bg-primary/10 text-primary border border-primary/15' : 'text-textMuted hover:text-textSub'
              }`}
            >
              <Activity size={14} /> Heatmap
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 relative overflow-hidden flex flex-col">
        {activeTab === 'graph' && (
          <div className="flex-1 flex flex-col">
            <div className="px-6 py-3 bg-surface border-b border-border flex gap-4 items-center shrink-0">
              <span className="text-xs text-textMuted font-mono">Фильтр:</span>
              <select
                value={filterType}
                onChange={(e) => setGraphState({ filterType: e.target.value })}
                className="bg-surfaceAlt border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary/30 text-textMain font-mono"
              >
                <option value="Все">Все</option>
                <option value="Противоречия">Противоречия</option>
                <option value="Дубли">Дубли</option>
                <option value="Устаревшие">Устаревшие</option>
              </select>

              <div className="ml-auto flex items-center gap-3 text-[10px] text-textDim font-mono">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-contradiction" /> Коллизия</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-duplicate" /> Дубль</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-outdated" /> Устаревшее</span>
              </div>
            </div>
            <iframe
              key={`${filterType}-${activeScope.join(',')}`}
              src={getGraphHtmlUrl(filterType, activeScope)}
              className="flex-1 w-full bg-white"
              title="Knowledge Graph"
              sandbox="allow-scripts allow-same-origin allow-popups allow-top-navigation-by-user-activation"
            />
          </div>
        )}

        {activeTab === 'heatmap' && (
          <div className="flex-1 p-8 overflow-auto">
            <div className="max-w-6xl mx-auto bg-surface p-6 rounded-xl border border-border">
              <h2 className="text-base font-display font-medium text-textMain mb-6 flex items-center gap-2">
                <Info size={16} className="text-primary" /> Тепловая карта проблемности
              </h2>
              {heatmapError ? (
                <div className="flex items-center justify-center h-64 text-textMuted text-sm">{heatmapError}</div>
              ) : plotData ? (
                <div className="w-full h-[600px] bg-white rounded-lg overflow-hidden">
                  <ErrorBoundary fallbackRender={({ error }: FallbackProps) => (
                     <div className="p-10 text-riskHighText bg-riskHigh/10 border border-riskHigh/20 h-full overflow-auto rounded-lg">
                       <strong>Ошибка рендеринга Plotly:</strong>
                       <pre className="mt-4 text-xs font-mono whitespace-pre-wrap">{error instanceof Error ? error.message : 'Неизвестная ошибка'}</pre>
                       <pre className="mt-2 opacity-50 text-[10px] font-mono whitespace-pre-wrap">{error instanceof Error ? error.stack : ''}</pre>
                     </div>
                  )}>
                    <Plot
                      data={plotData as never}
                      layout={{
                        ...(plotLayout ?? {}),
                        autosize: true,
                        margin: { t: 50, l: 200 },
                        paper_bgcolor: 'transparent',
                        plot_bgcolor: 'transparent',
                      }}
                      useResizeHandler={true}
                      style={{ width: '100%', height: '100%' }}
                    />
                  </ErrorBoundary>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64 text-textDim font-mono text-sm">
                  Загрузка...
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