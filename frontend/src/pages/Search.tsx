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

const normalizeScopeDocId = (docId: string) =>
  docId.endsWith('_current')
    ? docId.slice(0, -8)
    : docId.replace(/_\d+$/, '');

const SearchPage = () => {
  const navigate = useNavigate();
  const {
    activeScope, setActiveScope, setPendingMessage,
    searchQuery, searchResults, searchPreview,
    setSearchQuery, setSearchPreview, setSearchState, setSelectedDocId
  } = useStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [expandedIndicesText, setExpandedIndicesText] = useState<number[]>([]);
  const selectedResults = selectedIndices.map(i => searchResults[i]).filter(Boolean);

  const toggleTextExpand = (idx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedIndicesText(prev => prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]);
  };

  const handleSearch = async (q?: string) => {
    const searchQ = (q ?? searchQuery).trim();
    if (!searchQ) return;
    setSelectedIndices([]);

    const isSingleId = /^[a-zA-Z]\d+$/.test(searchQ.toUpperCase());
    if (isSingleId) {
      const docId = searchQ.toUpperCase();
      setLoading(true);
      setError('');
      setSearchState(searchQuery, [], null);
      try {
        const preview = await previewDocument(docId);
        setSearchState('', [], preview);
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } }; message?: string };
        setError(e.response?.data?.detail || e.message || 'Документ не найден на Adilet');
      } finally {
        setLoading(false);
      }
      return;
    }

    const isIdList = /^([a-zA-Z]\d+)(,\s*[a-zA-Z]\d+)*$/.test(searchQ.toUpperCase());
    if (isIdList) {
      setLoading(true);
      setError('');
      try {
        const idsList = searchQ.split(',').map(s => s.trim().toUpperCase());
        await buildIndex(idsList);
        setActiveScope(idsList);
        setSearchState('', [], null);
      } catch (err: unknown) {
        const e = err as { message?: string };
        setError(e.message || 'Ошибка индексации');
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
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Ошибка поиска');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDoc = async () => {
    if (!searchPreview) return;
    setLoading(true);
    try {
      await buildIndex([searchPreview.doc_id]);
      if (!activeScope.includes(searchPreview.doc_id)) {
        setActiveScope([...activeScope, searchPreview.doc_id]);
      }
      setSelectedDocId(searchPreview.doc_id);
      navigate(`/analyze/${searchPreview.doc_id}`);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Ошибка при подтверждении');
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
    setSelectedIndices(prev => prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]);
  };

  const showHero = searchResults.length === 0 && !loading;

  return (
    <div className="flex-1 h-full overflow-hidden relative">
      <div className="absolute inset-0 grain" />

      <div className="relative z-10 h-full flex flex-col items-center justify-start overflow-y-auto">
        <div className="w-full max-w-3xl px-6 pt-28 pb-16">

          {showHero && (
            <div className="text-center mb-12 animate-fade-up flex flex-col items-center">
              <div className="inline-flex items-center justify-center gap-2 mb-5 px-5 py-2 rounded-full border border-primary/20 bg-primary/10 backdrop-blur-sm shadow-sm">
                <span className="text-[11px] sm:text-xs text-primary font-extrabold font-mono tracking-[0.15em] uppercase">Интеллектуальный анализ законодательства</span>
              </div>
              <h1 className="text-7xl sm:text-[5.5rem] font-display font-black tracking-tighter mb-5 leading-none">
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-primaryStrong to-primary drop-shadow-sm">Lex</span>
                <span className="text-textMain">Lens</span>
              </h1>
              <p className="text-textSub text-lg sm:text-xl mb-10 max-w-2xl mx-auto leading-relaxed font-medium">
                Семантический поиск и NLI-аудит по законодательству РК
              </p>

              <div className="flex flex-wrap justify-center gap-2">
                <span className="text-xs text-textDim mr-1 self-center font-mono">Попробуй &gt;</span>
                {CHIPS.map((chip) => (
                  <button key={chip} className="chip" onClick={() => { setSearchQuery(chip); handleSearch(chip); }}>
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeScope.length > 0 && !searchPreview && (
            <div className="mb-5 flex flex-col items-center gap-2 bg-primary/5 border border-primary/15 rounded-xl py-3 px-5 max-w-full animate-fade-down mx-auto relative group">
              <span className="text-xs text-primary font-medium font-mono tracking-wider uppercase">
                Анализ: {activeScope.length} документов
              </span>
              <div className="flex gap-2 flex-wrap justify-center overflow-auto max-h-24">
                {activeScope.map((id: string) => (
                  <span key={id} className="text-[11px] font-mono bg-primary/10 px-2.5 py-1 rounded text-primary/80 border border-primary/10">{id}</span>
                ))}
              </div>
              <button
                onClick={() => setActiveScope([])}
                className="absolute top-2 right-2 p-1 text-textDim hover:text-riskHigh rounded transition opacity-50 group-hover:opacity-100"
                title="Очистить фильтр"
              >?</button>
            </div>
          )}

          {searchPreview && (
            <div className="mb-6 glass-warm rounded-2xl p-6 shadow-2xl animate-fade-up">
              <div className="flex justify-between items-start gap-4">
                <div className="space-y-3 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 bg-primary/15 text-primary text-[10px] font-bold uppercase tracking-wider rounded border border-primary/20 font-mono">
                      Adilet
                    </span>
                    <span className="text-xs text-textMuted font-mono">ID: {searchPreview.doc_id}</span>
                  </div>
                  <h2 className="text-xl font-display font-bold text-textMain leading-snug">{searchPreview.title}</h2>
                  <div className="flex gap-4 text-xs text-textMuted font-mono">
                    <span>Дата: {searchPreview.date || '—'}</span>
                    <span>Версий: {searchPreview.versions_found}</span>
                  </div>
                </div>
                <div className="shrink-0 w-12 h-12 rounded-xl bg-primary/10 border border-primary/15 flex items-center justify-center">
                  <FileText className="text-primary" size={24} />
                </div>
              </div>
              <div className="mt-6 flex gap-3">
                <button
                  onClick={handleConfirmDoc}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-primary hover:bg-primaryHover text-surface rounded-xl font-bold transition-all shadow-lg shadow-primaryShadow/10"
                >
                  {loading ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
                  Подтвердить и индексировать
                </button>
                <button
                  onClick={() => setSearchPreview(null)}
                  className="px-5 py-3 bg-surfaceAlt border border-border text-textSub rounded-xl font-bold hover:bg-surfaceHover transition"
                >Отмена</button>
              </div>
            </div>
          )}

          <div className={`glass rounded-2xl p-4 input-glow transition-all ${showHero ? 'animate-fade-up' : ''}`} style={{ animationDelay: '0.15s' }}>
            <textarea
              rows={2}
              className="w-full bg-transparent text-textMain placeholder-textDim resize-none outline-none text-sm leading-relaxed font-body"
              placeholder="Задайте вопрос о законодательстве или введите ID (например, K1500000377)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSearch(); }
              }}
            />
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
              <span className="text-xs text-textDim font-mono">
                {loading ? '? Поиск...' : 'Enter — поиск'}
              </span>
              <button
                onClick={() => handleSearch()}
                disabled={loading || !searchQuery.trim()}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  searchQuery.trim() && !loading
                    ? 'bg-primary hover:bg-primaryHover text-surface shadow-lg shadow-primaryShadow/20'
                    : 'bg-surfaceAlt text-textDim cursor-not-allowed'
                }`}
              >
                {loading
                  ? <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                  : <Send size={15} />
                }
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3 animate-fade-up">
              <div className="flex items-center justify-between px-1">
                <p className="text-xs text-textMuted font-mono">{searchResults.length} результатов</p>
                <div className="flex items-center gap-4">
                  {searchResults.length >= 2 && (
                    <p className="text-xs text-primary/70">Выберите документы для анализа</p>
                  )}
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setSearchState('', [], null);
                      setSelectedIndices([]);
                    }}
                    className="text-xs font-mono text-textMuted hover:text-riskHigh transition-colors bg-surfaceAlt px-2 py-1 rounded"
                  >
                    ? Очистить поиск
                  </button>
                </div>
              </div>
              {searchResults.map((res: { doc_id: string; title: string; text?: string; excerpt?: string; score?: number; cosine_score?: number; bm25_score?: number }, idx: number) => {
                const isSelected = selectedIndices.includes(idx);
                const isTextExpanded = expandedIndicesText.includes(idx);
                return (
                  <div
                    key={idx}
                    className={`glass rounded-xl p-4 cursor-pointer group transition-all relative ${
                      isSelected
                        ? 'border-primary/30 bg-primary/5 ring-1 ring-primary/20'
                        : 'hover:border-primary/15 hover:bg-white/[0.02]'
                    }`}
                    onClick={() => toggleSelect(idx)}
                  >
                    {isSelected && (
                      <div className="absolute top-2.5 right-2.5 bg-primary text-surface text-[10px] px-2 py-0.5 rounded font-bold uppercase z-10 flex items-center gap-1 font-mono">
                        <Check size={10} /> Выбран
                      </div>
                    )}
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 border transition-colors ${
                          isSelected ? 'bg-primary/15 border-primary/25' : 'bg-surfaceAlt border-border'
                        }`}>
                          <FileText size={14} className={isSelected ? 'text-primary' : 'text-textMuted'} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h3 className="font-display font-semibold text-sm text-textMain group-hover:text-primary transition truncate pr-8">{res.title}</h3>
                          <p className="text-textDim text-xs mt-0.5 font-mono">ID: {res.doc_id}</p>
                          <div className="mt-1 relative">
                            <p className={`text-textMuted text-xs leading-relaxed ${isTextExpanded ? '' : 'line-clamp-2'}`}>
                              {res.text || res.excerpt}
                            </p>
                            <button
                              onClick={(e) => toggleTextExpand(idx, e)}
                              className="text-[10px] text-primary/80 hover:text-primary font-bold uppercase tracking-wider mt-1 transition-colors"
                            >
                              {isTextExpanded ? 'Свернуть' : 'Читать полностью'}
                            </button>
                          </div>
                        </div>
                      </div>
                      <ArrowRight size={15} className="text-textDim group-hover:text-primary transition shrink-0 mt-1" />
                    </div>

                    <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-border/50">
                      <div className="flex items-center gap-3 text-xs text-textDim font-mono">
                        <span>RRF <span className="text-textSub">{res.score?.toFixed(3)}</span></span>
                        <span className="text-border">|</span>
                        <span>FAISS <span className="text-riskLow">{res.cosine_score?.toFixed(3)}</span></span>
                        <span className="text-border">|</span>
                        <span>BM25 <span className="text-accent">{res.bm25_score?.toFixed(1)}</span></span>
                      </div>
                      <button
                        onClick={(e) => handleAskAI(e, res.text || res.excerpt || '')}
                        className="flex items-center gap-1 text-xs text-primary/70 hover:text-primary transition"
                      >
                        <MessageSquareText size={13} /> AI
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {error && (
            <div className="mt-4 bg-riskHigh/10 rounded-xl p-4 border border-riskHigh/20 text-riskHighText font-medium text-sm text-center">
              {error}
            </div>
          )}
        </div>

        {showHero && (
          <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-6 text-xs text-textDim">
            <span>Нажмите <kbd className="px-1.5 py-0.5 bg-surfaceAlt rounded border border-border text-textMuted font-mono text-[10px]">Enter</kbd> для поиска</span>
            <span>·</span>
            <span>ID закона (K...) &gt; прямой анализ</span>
          </div>
        )}

        {selectedResults.length > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 p-4 bg-surface/95 backdrop-blur-xl border border-primary/20 rounded-2xl shadow-xl shadow-primaryShadow/10 flex items-center gap-4 animate-fade-up z-50">
            <span className="text-textMain font-display font-semibold whitespace-nowrap">Выбрано: {selectedResults.length}</span>
            {selectedResults.length === 1 && (
              <>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedDocId(selectedResults[0].doc_id);
                    navigate(`/analyze/${selectedResults[0].doc_id}`);
                  }}
                  className="px-5 py-2 bg-primary hover:bg-primaryHover text-surface rounded-lg font-bold transition"
                >Анализ</button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    const docId = normalizeScopeDocId(selectedResults[0].doc_id);
                    setActiveScope([docId]);
                    navigate('/diff');
                  }}
                  className="px-5 py-2 bg-riskMedium hover:bg-primaryStrong text-surface rounded-lg font-bold transition"
                >Diff</button>
              </>
            )}
            {selectedResults.length >= 2 && (
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  const ids = [...new Set(selectedResults.map((r: { doc_id: string }) => r.doc_id))];
                  setLoading(true);
                  try { await buildIndex(ids); setActiveScope(ids); navigate('/audit'); }
                  catch (err: unknown) { const er = err as { message?: string }; setError(er.message || 'Ошибка'); }
                  finally { setLoading(false); }
                }}
                className="px-5 py-2 bg-primary hover:bg-primaryHover text-surface rounded-lg font-bold flex items-center gap-2 transition"
                disabled={loading}
              >
                {loading && <Loader2 className="animate-spin" size={16} />}
                Комплексный аудит ({[...new Set(selectedResults.map((r: { doc_id: string }) => r.doc_id))].length})
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
                className="px-5 py-2 bg-riskMedium hover:bg-primaryStrong text-surface rounded-lg font-bold transition"
              >Diff</button>
            )}
            <button onClick={() => setSelectedIndices([])} className="text-textDim hover:text-textMain px-2 transition">Сброс</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;