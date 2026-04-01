import React, { useState } from 'react';
import { searchDocuments } from '../services/api';
import { Send, FileText, ArrowRight, MessageSquareText } from 'lucide-react';
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
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const toggleSidebar = useStore((state: any) => state.toggleSidebar);
  const addMessage = useStore((state: any) => state.addMessage);

  const handleSearch = async (q?: string) => {
    const searchQ = (q ?? query).trim();
    if (!searchQ) return;

    if (/^[a-zA-Z]\d+/.test(searchQ.toUpperCase())) {
      navigate(`/analyze/${searchQ.toUpperCase()}`);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await searchDocuments(searchQ);
      setResults(data.results || []);
    } catch (err: any) {
      setError(err.message || 'Ошибка поиска');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleAskAI = (e: React.MouseEvent, text: string) => {
    e.stopPropagation();
    addMessage({ role: 'user', content: `Объясни подробнее вот этот отрывок закона:\n\n"${text}"` });
    toggleSidebar?.();
  };

  const showHero = results.length === 0 && !loading;

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
                    onClick={() => { setQuery(chip); handleSearch(chip); }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search input */}
          <div className={`glass rounded-2xl p-4 input-glow transition-all ${showHero ? 'animate-fade-up' : ''}`}>
            <textarea
              rows={2}
              className="w-full bg-transparent text-textMain placeholder-textMuted resize-none outline-none text-sm leading-relaxed"
              placeholder="Задайте вопрос о законодательстве или введите ID документа (напр. K1500000377)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
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
                disabled={loading || !query.trim()}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  query.trim() && !loading
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
          {results.length > 0 && (
            <div className="mt-6 space-y-3 animate-fade-up">
              <p className="text-xs text-textMuted px-1">Найдено {results.length} результатов</p>
              {results.map((res: any, idx) => (
                <div
                  key={idx}
                  className="glass rounded-xl p-4 hover:border-indigo-500/30 cursor-pointer group transition-all hover:bg-white/5"
                  onClick={() => navigate(`/analyze/${res.doc_id}`)}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 mt-0.5">
                        <FileText size={14} className="text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-sm text-textMain group-hover:text-indigo-300 transition truncate">{res.title}</h3>
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
                      onClick={(e) => handleAskAI(e, res.excerpt)}
                      className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition"
                    >
                      <MessageSquareText size={13} /> Спросить AI
                    </button>
                  </div>
                </div>
              ))}
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
      </div>
    </div>
  );
};

export default SearchPage;
