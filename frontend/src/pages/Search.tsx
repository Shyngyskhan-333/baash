import React, { useState } from 'react';
import { searchDocuments, buildIndex, previewDocument } from '../services/api';
import { Send, FileText, ArrowRight, MessageSquareText, Check, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';

const CHIPS = [
  'Штраф за нарушение экологических норм',
  'Права работника при увольнении',
  'Лицензирование медицинской деятельности',
  'Налоговые льготы для ИП',
  'Защита персональных данных',
];

const SearchPage = () => {
  const navigate = useNavigate();
  const { 
    activeScope, 
    setActiveScope, 
    setPendingMessage,
    searchQuery,
    searchResults,
    searchPreview,
    setSearchQuery,
    setSearchPreview,
    setSearchState,
    setSelectedDocId
  } = useStore();


  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);

  // Derive selected results from indices
  const selectedResults = selectedIndices.map(i => searchResults[i]).filter(Boolean);

  const handleSearch = async (q?: string) => {
    const searchQ = (q ?? searchQuery).trim();
    if (!searchQ) return;

    // Reset selection on new search
    setSelectedIndices([]);

    // Check if it's a Document ID (e.g. K2000000350)
    const isSingleId = /^[a-zA-Z]\d+$/.test(searchQ.toUpperCase());
    
    if (isSingleId) {
      const docId = searchQ.toUpperCase();
      console.log("[DEBUG] Fetching preview for:", docId);
      setLoading(true);
      setError('');
      setSearchState(searchQuery, [], null); // clear and set null
      try {
        const preview = await previewDocument(docId);
        setSearchState('', [], preview);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Документ не найден на Adilet');
      } finally {
        setLoading(false);
      }
      return;
    }

    // Check if it's a comma-separated list of Document IDs
    const isIdList = /^([a-zA-Z]\d+)(,\s*[a-zA-Z]\d+)*$/.test(searchQ.toUpperCase());
    
    if (isIdList) {
      setLoading(true);
      setError('');
      try {
        const idsList = searchQ.split(',').map(s => s.trim().toUpperCase());
        await buildIndex(idsList);
        setActiveScope(idsList);
        setSearchState('', [], null);
      } catch (err: any) {
        setError(err.message || 'Ошибка индексации');
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    setError('');
    setSearchState(searchQ, [], null);
    try {
      const data = await searchDocuments(searchQ, 10, undefined, activeScope);
      setSearchState(searchQ, data.results || [], null);
    } catch (err: any) {
      setError(err.message || 'Ошибка поиска');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDoc = async () => {
    if (!searchPreview) return;
    setLoading(true);
    try {
      console.log("[INDEX] Confirming indexing for:", searchPreview.doc_id);
      await buildIndex([searchPreview.doc_id]);
      
      // Накопительный выбор: добавляем, если еще нет в списке
      if (!activeScope.includes(searchPreview.doc_id)) {
        setActiveScope([...activeScope, searchPreview.doc_id]);
      }
      
      setSelectedDocId(searchPreview.doc_id);
      navigate(`/analyze/${searchPreview.doc_id}`);
    } catch (err: any) {
      setError(err.message || 'Ошибка при подтверждении');
    } finally {
      setLoading(false);
      setSearchState('', [], null);
    }
  };


  const handleAskAI = (e: React.MouseEvent, fullText: string) => {
    e.stopPropagation();
    setPendingMessage(`Объясни подробнее вот этот отрывок закона:\n\n"${fullText}"`);
  };

  const toggleSelect = (idx: number) => {
    setSelectedIndices(prev => 
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const showHero = searchResults.length === 0 && !loading;

  return (
    <div className="flex-1 h-full overflow-hidden relative">
      {/* Night background */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/night_bg.png')" }}
      />
      <div className="hero-overlay absolute inset-0" />

      {/* Stars overlay */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(30)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white"
            style={{
              width: Math.random() * 2 + 1 + 'px',
              height: Math.random() * 2 + 1 + 'px',
              left: Math.random() * 100 + '%',
              top: Math.random() * 60 + '%',
              opacity: Math.random() * 0.7 + 0.2,
              animation: `twinkle ${2 + Math.random() * 4}s ease-in-out infinite`,
              animationDelay: Math.random() * 4 + 's',
            }}
          />
        ))}
      </div>

      {/* Main content */}
      <div className="relative z-10 h-full flex flex-col items-center justify-start overflow-y-auto">
        <div className="w-full max-w-3xl px-6 pt-28 pb-16">

          {showHero && (
            <div className="text-center mb-10 animate-fade-up">
              <h1 className="text-5xl font-extrabold tracking-tight mb-3 leading-tight">
                Анализируй.{' '}
                <span className="text-indigo-400">Мы сделаем остальное.</span>
              </h1>
              <p className="text-textSub text-lg mb-6">
                Введи запрос по законодательству Казахстана — получи ответ за секунды.
              </p>

              {/* Chips */}
              <div className="flex flex-wrap justify-center gap-2 mb-8">
                <span className="text-xs text-textMuted mr-1 self-center">Попробуй →</span>
                {CHIPS.map((chip) => (
                  <button
                    key={chip}
                    className="chip"
                    onClick={() => { setSearchQuery(chip); handleSearch(chip); }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Scope Badge */}
          {activeScope && activeScope.length > 0 && !searchPreview && (
            <div className="mb-4 flex flex-col items-center gap-2 bg-indigo-900/40 border border-indigo-500/50 rounded-xl py-3 px-5 shadow-lg max-w-full animate-fade-down mx-auto relative group">
              <span className="text-xs text-indigo-300 font-medium">
                Поиск и аудит ограничены документами ({activeScope.length}):
              </span>
              <div className="flex gap-2 flex-wrap justify-center overflow-auto max-h-24">
                {activeScope.map((id: string) => (
                   <span key={id} className="text-xs font-mono bg-white/10 px-2 py-1 rounded text-white border border-white/5">{id}</span>
                ))}
              </div>
              <button 
                onClick={() => setActiveScope([])}
                className="absolute top-2 right-2 p-1 text-indigo-400 hover:bg-white/10 hover:text-red-400 rounded transition opacity-50 group-hover:opacity-100"
                title="Очистить фильтр и вернуться к глобальному поиску"
              >
                ✕
              </button>
            </div>
          )}

          {/* Preview Card */}
          {searchPreview && (
            <div className="mb-6 glass border-indigo-500/50 rounded-2xl p-6 shadow-2xl animate-fade-up">
              <div className="flex justify-between items-start gap-4">
                <div className="space-y-3 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-wider rounded border border-indigo-500/30">
                      Әділет Парсер
                    </span>
                    <span className="text-xs text-textMuted font-mono">ID: {searchPreview.doc_id}</span>
                  </div>
                  <h2 className="text-xl font-bold text-white leading-snug">{searchPreview.title}</h2>
                  <div className="flex gap-4 text-xs text-textMuted">
                    <span>Дата: {searchPreview.date || 'Не указана'}</span>
                    <span>Версий найдено: {searchPreview.versions_found}</span>
                  </div>
                </div>
                <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <FileText className="text-indigo-400" size={24} />
                </div>
              </div>
              
              <div className="mt-6 flex gap-3">
                <button
                  onClick={handleConfirmDoc}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-indigo-600/30"
                >
                  {loading ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
                  Подтвердить и Адаптировать
                </button>
                <button
                  onClick={() => setSearchPreview(null)}
                  className="px-4 py-3 bg-white/5 border border-white/10 text-white rounded-xl font-bold hover:bg-white/10 transition"
                >
                  Отмена
                </button>
              </div>
              <p className="mt-4 text-[10px] text-textMuted text-center uppercase tracking-widest opacity-50">
                Нажмите подтвердить, чтобы перестроить анализ, граф и аудит под этот документ
              </p>
            </div>
          )}

          {/* Search input */}
          <div className={`glass rounded-2xl p-4 input-glow transition-all ${showHero ? 'animate-fade-up' : ''}`}>
            <textarea
              rows={2}
              className="w-full bg-transparent text-textMain placeholder-textMuted resize-none outline-none text-sm leading-relaxed"
              placeholder="Задайте вопрос о законодательстве или введите ID документа (напр. K1500000377)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch();
                }
              }}
            />
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
              <span className="text-xs text-textMuted">
                {loading ? 'Поиск...' : 'Нажмите Enter для поиска'}
              </span>
              <button
                onClick={() => handleSearch()}
                disabled={loading || !searchQuery.trim()}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  searchQuery.trim() && !loading
                    ? 'bg-primary hover:bg-primaryHover text-white shadow-lg shadow-indigo-500/30'
                    : 'bg-white/10 text-textMuted cursor-not-allowed'
                }`}
              >
                {loading
                  ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  : <Send size={15} />
                }
              </button>
            </div>
          </div>

          {/* Results */}
          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3 animate-fade-up">
              <div className="flex items-center justify-between px-1">
                <p className="text-xs text-textMuted">Найдено {searchResults.length} результатов</p>
                {searchResults.length >= 2 && (
                  <p className="text-xs text-indigo-400">Нажмите на карточки, чтобы выбрать документы для анализа</p>
                )}
              </div>
              {searchResults.map((res: any, idx: number) => {
                const isSelected = selectedIndices.includes(idx);
                return (
                <div
                  key={idx}
                  className={`glass rounded-xl p-4 hover:border-indigo-500/30 cursor-pointer group transition-all hover:bg-white/5 relative ${isSelected ? 'border-indigo-500/50 bg-indigo-500/10 ring-1 ring-indigo-500/40' : ''}`}
                  onClick={() => toggleSelect(idx)}
                >
                  {isSelected && (
                     <div className="absolute top-2 right-2 bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded font-bold uppercase z-10 flex items-center gap-1">
                        <Check size={10} /> Выбран
                     </div>
                  )}
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 border transition-colors ${isSelected ? 'bg-indigo-500/30 border-indigo-500/50' : 'bg-indigo-500/10 border-indigo-500/20'}`}>
                        <FileText size={14} className="text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-sm text-textMain group-hover:text-indigo-300 transition truncate">{res.title}</h3>
                        <p className="text-textMuted text-xs mt-0.5 font-mono">ID: {res.doc_id}</p>
                        <p className="text-textMuted text-xs mt-1 line-clamp-2 leading-relaxed">{res.excerpt}</p>
                      </div>
                    </div>
                    <ArrowRight size={15} className="text-textMuted group-hover:text-indigo-400 transition shrink-0 mt-1" />
                  </div>

                  <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-white/5">
                    <div className="flex items-center gap-3 text-xs text-textMuted font-mono">
                      <span>RRF <span className="text-white">{res.score?.toFixed(3)}</span></span>
                      <span className="text-border">|</span>
                      <span>FAISS <span className="text-emerald-400">{res.cosine_score?.toFixed(3)}</span></span>
                      <span className="text-border">|</span>
                      <span>BM25 <span className="text-blue-400">{res.bm25_score?.toFixed(1)}</span></span>
                    </div>
                    <button
                      onClick={(e) => handleAskAI(e, res.text || res.excerpt)}
                      className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition"
                    >
                      <MessageSquareText size={13} /> Спросить AI
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
          )}

          {error && (
            <div className="mt-4 glass rounded-xl p-4 border-red-500/20 text-red-400 text-sm text-center">
              {error}
            </div>
          )}
        </div>

        {/* Bottom hint */}
        {showHero && (
          <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-6 text-xs text-textMuted/50">
            <span>Нажмите <kbd className="px-1.5 py-0.5 bg-white/5 rounded border border-white/10 text-textMuted">Enter</kbd> для поиска</span>
            <span>·</span>
            <span>Используйте ID закона (K...) для перехода к анализу</span>
          </div>
        )}

        {/* Selected Documents Action Bar */}
        {selectedResults.length > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 p-4 bg-surface border border-indigo-500 rounded-2xl shadow-[0_0_40px_rgba(99,102,241,0.4)] flex items-center gap-4 animate-fade-up z-50">
            <span className="text-white font-semibold whitespace-nowrap">Выбрано: {selectedResults.length}</span>
            {selectedResults.length === 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedDocId(selectedResults[0].doc_id);
                  navigate(`/analyze/${selectedResults[0].doc_id}`);
                }}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold"
              >
                Одиночный Анализ
              </button>
            )}
            {selectedResults.length >= 2 && (
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  // Deduplicate doc_ids
                  const ids = [...new Set(selectedResults.map((r: any) => r.doc_id))];
                  setLoading(true);
                  try {
                    await buildIndex(ids);
                    setActiveScope(ids);
                    navigate('/audit');
                  } catch (err: any) {
                    setError(err.message || 'Ошибка индексации');
                  } finally {
                    setLoading(false);
                  }
                }}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold flex items-center gap-2"
                disabled={loading}
              >
                {loading && <Loader2 className="animate-spin" size={16} />}
                Комплексный Анализ ({[...new Set(selectedResults.map((r: any) => r.doc_id))].length} док.)
              </button>
            )}
            {selectedResults.length === 2 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  useStore.getState().setDiffState({
                    textA: selectedResults[0].text || selectedResults[0].excerpt,
                    textB: selectedResults[1].text || selectedResults[1].excerpt,
                    result: null
                  });
                  navigate('/diff');
                }}
                className="px-6 py-2 bg-[#f59e0b] hover:bg-[#d97706] text-white rounded-lg font-bold"
              >
                Сравнить (Diff)
              </button>
            )}
            <button onClick={() => setSelectedIndices([])} className="text-textMuted hover:text-white px-2">
              Сброс
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
