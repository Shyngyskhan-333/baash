import { useState } from 'react';
import { diffDocuments } from '../services/api';
import { Columns, AlignLeft, Layers, Loader2, GitMerge } from 'lucide-react';

const DiffPage = () => {
  const [textA, setTextA] = useState('');
  const [textB, setTextB] = useState('');
  const [mode, setMode] = useState<'split' | 'unified'>('split');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleDiff = async () => {
    if (!textA || !textB) return;
    setLoading(true);
    setError('');
    try {
      const data = await diffDocuments(textA, textB);
      setResult(data);
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
              onClick={() => setMode('split')}
            ><Columns size={18}/> Split</button>
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-md font-semibold transition ${mode === 'unified' ? 'bg-[#2d3748] text-white shadow' : 'text-textMuted hover:text-white'}`}
              onClick={() => setMode('unified')}
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
                onChange={e => setTextA(e.target.value)}
              />
            </div>
            <div className="flex-1 flex flex-col gap-2 relative">
              <label className="text-sm font-bold uppercase tracking-wide text-textMuted">Новая редакция / Текст B</label>
              <textarea 
                className="flex-1 bg-background border border-[#2d3748] rounded-xl p-4 text-white resize-none outline-none focus:border-primary transition font-mono leading-relaxed"
                placeholder="Вставьте измененный текст сюда..."
                value={textB}
                onChange={e => setTextB(e.target.value)}
              />
            </div>
          </div>
          
          <div className="text-center">
            <button 
              className="px-8 py-4 bg-primary hover:bg-primaryHover text-white font-bold text-lg rounded-full shadow-xl transition transform hover:scale-105"
              onClick={handleDiff}
              disabled={loading || !textA || !textB}
            >
              {loading ? <span className="flex items-center gap-2"><Loader2 className="animate-spin" /> Анализируем AI...</span> : 'Сравнить и Анализировать'}
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
            
            <button className="text-textMuted hover:text-white transition flex items-center gap-2 font-medium bg-[#2d3748] px-4 py-2 rounded-lg" onClick={() => setResult(null)}>
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
