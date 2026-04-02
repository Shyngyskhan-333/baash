import { useState, useEffect } from 'react';
import { diffDocuments, fetchDocument, previewDocument } from '../services/api';
import { Columns, AlignLeft, Layers, Loader2, GitMerge } from 'lucide-react';
import { useStore } from '../store/useStore';

const DiffPage = () => {
  const { activeScope, diffState, setDiffState } = useStore();
  const { textA, textB, result, mode } = diffState;

  const [isAutoLoading, setIsAutoLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // If we have an active document, try to auto-load versions
    if (activeScope.length === 1 && !textA && !textB) {
      const docId = activeScope[0];
      const loadVersions = async () => {
        setIsAutoLoading(true);
        try {
          // 1. Get metadata to find version IDs
          const meta = await previewDocument(docId);
          // 2. Fetch current
          const current = await fetchDocument(docId);
          setDiffState({ textB: current.text });
          // 3. Fetch previous if available
          const prevVer = meta.versions.find((v: any) => v.status === 'archived');
          if (prevVer) {
            const previous = await fetchDocument(prevVer.version_id);
            setDiffState({ textA: previous.text });
          } else {
             setDiffState({ textA: current.text }); // Fallback to same text if no archive
          }
        } catch (err: any) {
          console.error("Auto-load failed:", err);
        } finally {
          setIsAutoLoading(false);
        }
      };
      loadVersions();
    }
  }, [activeScope, textA, textB, setDiffState]);

  const handleDiff = async () => {
    if (!textA || !textB) return;
    setLoading(true);
    setError('');
    try {
      const data = await diffDocuments(textA, textB);
      setDiffState({ result: data });
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Ошибка сравнения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col pt-20 bg-background overflow-hidden relative h-full">
      <div className="px-10 pb-4">
        {error && (
          <div className="mb-4 p-3 bg-red-900/20 border border-red-500/40 rounded-lg text-red-300 text-sm">{error}</div>
        )}
      </div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-extrabold flex items-center gap-3">
            <GitMerge className="text-primary"/> Анализ Изменений (Diff)
          </h1>
          <p className="text-textMuted mt-2">Сравнение текстов или разных редакций закона на семантическое совпадение.</p>
        </div>
        
        {result && (
          <div className="flex bg-surface rounded-lg p-1 border border-[#2d3748] shadow-lg">
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-md font-semibold transition ${mode === 'split' ? 'bg-[#2d3748] text-white shadow' : 'text-textMuted hover:text-white'}`}
              onClick={() => setDiffState({ mode: 'split' })}
            ><Columns size={18}/> Split</button>
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-md font-semibold transition ${mode === 'unified' ? 'bg-[#2d3748] text-white shadow' : 'text-textMuted hover:text-white'}`}
              onClick={() => setDiffState({ mode: 'unified' })}
            ><AlignLeft size={18}/> Unified</button>
          </div>
        )}
      </div>

      {!result ? (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-6xl mx-auto h-[70vh]">
          <div className="flex flex-1 gap-6 w-full shadow-2xl rounded-2xl p-6 bg-surface border border-[#2d3748]">
            <div className="flex-1 flex flex-col gap-2 relative">
              <label className="text-sm font-bold uppercase tracking-wide text-textMuted">Старая редакция / Текст А</label>
              <textarea 
                className="flex-1 bg-background border border-[#2d3748] rounded-xl p-4 text-white resize-none outline-none focus:border-primary transition font-mono leading-relaxed"
                placeholder="Вставьте исходный текст сюда..."
                value={textA}
                onChange={e => setDiffState({ textA: e.target.value })}
              />
            </div>
            <div className="flex-1 flex flex-col gap-2 relative">
              <label className="text-sm font-bold uppercase tracking-wide text-textMuted">Новая редакция / Текст B</label>
              <textarea 
                className="flex-1 bg-background border border-[#2d3748] rounded-xl p-4 text-white resize-none outline-none focus:border-primary transition font-mono leading-relaxed"
                placeholder="Вставьте измененный текст сюда..."
                value={textB}
                onChange={e => setDiffState({ textB: e.target.value })}
              />
            </div>
          </div>
          
          <div className="text-center">
            <button 
              className="px-8 py-4 bg-primary hover:bg-primaryHover text-white font-bold text-lg rounded-full shadow-xl transition transform hover:scale-105"
              onClick={handleDiff}
              disabled={loading || isAutoLoading || !textA || !textB}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="animate-spin" /> Анализируем AI...
                </span>
              ) : isAutoLoading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="animate-spin" /> Загружаем версии...
                </span>
              ) : (
                'Сравнить и Анализировать'
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden bg-surface border border-[#2d3748] rounded-2xl shadow-2xl relative">
          
          <div className="p-6 border-b border-[#2d3748] bg-[#0f1117]/50 flex items-center justify-between">
            <div className="flex items-center gap-6">
               <div className="flex gap-4 font-mono text-sm">
                 <span className="text-riskLow bg-riskLow/10 px-3 py-1 rounded border border-riskLow">Добавлено: {result.stats.added}</span>
                 <span className="text-riskHigh bg-riskHigh/10 px-3 py-1 rounded border border-riskHigh">Удалено: {result.stats.removed}</span>
                 <span className="text-riskMedium bg-riskMedium/10 px-3 py-1 rounded border border-riskMedium">Изменено: {result.stats.changed}</span>
               </div>
            </div>
            
            <button className="text-textMuted hover:text-white transition flex items-center gap-2 font-medium bg-[#2d3748] px-4 py-2 rounded-lg" onClick={() => setDiffState({ result: null })}>
              <span className="text-lg">×</span> Закрыть
            </button>
          </div>
          
          <div className="p-6 border-b border-[#2d3748] bg-primary/10">
            <div className="flex items-start gap-3">
              <Layers className="text-primary mt-1 shrink-0" />
              <div>
                <h3 className="font-bold text-white mb-1">AI Резюме Изменений</h3>
                <p className="text-textMain/90 font-medium leading-relaxed">{result.ai_summary}</p>
              </div>
            </div>
          </div>

          <div className={`flex-1 overflow-y-auto p-0 font-mono text-sm leading-loose ${mode === 'split' ? 'flex' : 'block'}`}>
            {result.hunks.map((hunk: any, idx: number) => {
              if (mode === 'split') {
                return (
                  <div key={idx} className="flex w-full divide-x divide-[#2d3748] border-b border-[#2d3748]">
                    <div className={`flex-1 p-4 ${hunk.type === 'removed' || hunk.type === 'changed' ? 'bg-[#ef4444]/10' : ''}`}>
                      <div className="text-textMuted mb-2 text-xs select-none">Строка {hunk.line_number} (Старая версия)</div>
                      <div className="whitespace-pre-wrap">{hunk.old_text || ''}</div>
                    </div>
                    <div className={`flex-1 p-4 ${hunk.type === 'added' || hunk.type === 'changed' ? 'bg-[#22c55e]/10' : ''}`}>
                      <div className="text-textMuted mb-2 text-xs select-none">Строка {hunk.line_number} (Новая версия)</div>
                      <div className="whitespace-pre-wrap">{hunk.new_text || ''}</div>
                    </div>
                  </div>
                );
              } else {
                return (
                  <div key={idx} className="border-b border-[#2d3748]">
                    {hunk.old_text && (
                       <div className="flex">
                         <div className="w-12 text-center text-textMuted bg-[#2d3748]/30 py-2 border-r border-[#2d3748] select-none">-</div>
                         <div className="flex-1 p-2 whitespace-pre-wrap bg-[#ef4444]/10 text-[#fca5a5]">{hunk.old_text}</div>
                       </div>
                    )}
                    {hunk.new_text && (
                       <div className="flex">
                         <div className="w-12 text-center text-textMuted bg-[#2d3748]/30 py-2 border-r border-[#2d3748] select-none">+</div>
                         <div className="flex-1 p-2 whitespace-pre-wrap bg-[#22c55e]/10 text-[#86efac]">{hunk.new_text}</div>
                       </div>
                    )}
                  </div>
                );
              }
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default DiffPage;
