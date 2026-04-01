import { useState } from 'react';
import { runGlobalAudit } from '../services/api';
import { Search, AlertTriangle, FileWarning, HelpCircle } from 'lucide-react';

const GlobalAudit: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const startAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runGlobalAudit();
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Ошибка при выполнении аудита.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-background">
      <div className="max-w-5xl mx-auto space-y-8 px-8 pt-28 pb-16">
        <header>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-red-400 to-orange-400 mb-2">
            Аудит Коллизий O(N)
          </h1>
          <p className="text-textMuted text-lg mb-4">
            Моментальный поиск противоречий, дубликатов и устаревших норм по всей базе законов.
          </p>
          <div className="bg-[#1a202c] border border-[#2d3748] rounded px-4 py-3 inline-block font-mono text-sm text-indigo-300">
            Пайплайн: Top-10 (FAISS) {'->'} Cosine {'>'} 0.90 {'->'} Top-5 (NLI) {'->'} LLM JSON
          </div>
        </header>

        <button
          onClick={startAudit}
          disabled={loading}
          className={`flex items-center gap-2 px-6 py-3 border border-red-500 rounded font-bold transition ${
            loading ? 'bg-red-900/40 text-red-500 cursor-not-allowed' : 'bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white'
          }`}
        >
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
              Анализ O(N)... Это займет некоторое время
            </div>
          ) : (
            <>
              <Search size={18} />
              --detect-contradictions
            </>
          )}
        </button>

        {error && <div className="text-red-400 p-4 border border-red-500/50 rounded bg-red-900/20">{error}</div>}

        {results && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Contradictions */}
            <section>
              <h2 className="text-xl font-bold text-red-400 flex items-center gap-2 border-b border-[#2d3748] pb-2 mb-4">
                <AlertTriangle size={20} /> Противоречия (Коллизии): {results.stats.contradictions}
              </h2>
              <div className="space-y-4">
                {results.contradictions.map((p: any, i: number) => (
                  <div key={i} className="bg-surface border border-red-500/30 rounded-xl overflow-hidden shadow-lg shadow-black/20">
                    <div className="p-4 bg-red-500/10 border-b border-red-500/20 font-medium text-red-200">
                      Противоречие: {p.chunk_a.article_number} vs {p.chunk_b.article_number}
                    </div>
                    <div className="p-4 grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <strong className="block text-indigo-300">{p.chunk_a.doc_title}</strong>
                        <p className="text-sm bg-[#1a202c] p-3 rounded">{p.chunk_a.text}</p>
                      </div>
                      <div className="space-y-2">
                        <strong className="block text-orange-300">{p.chunk_b.doc_title}</strong>
                        <p className="text-sm bg-red-900/20 border border-red-500/30 p-3 rounded">{p.chunk_b.text}</p>
                      </div>
                    </div>
                    <div className="p-4 bg-[#1a202c] flex items-center justify-between text-sm">
                      <span className="text-textMuted">DeBERTa NLI (Доверие): ~{(p.scores.nli_confidence * 100).toFixed(0)}%</span>
                    </div>
                    {p.explanation && (
                      <div className="p-4 border-t border-[#2d3748] bg-surface">
                        <strong className="block mb-2 text-indigo-400 text-sm">LLM Объяснение:</strong>
                        <pre className="text-xs text-textMuted overflow-auto p-4 rounded bg-[#0d1117] border border-[#2d3748]">
                          {JSON.stringify(p.explanation, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* Duplicates */}
            <section>
              <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2 border-b border-[#2d3748] pb-2 mb-4">
                <FileWarning size={20} /> Дубликаты (Смежные): {results.stats.duplicates}
              </h2>
              <div className="space-y-4">
                {results.duplicates.map((p: any, i: number) => (
                  <div key={i} className="bg-surface border border-blue-500/30 rounded-xl p-4 space-y-3">
                    <div className="font-medium text-blue-300 flex justify-between">
                      <span>{p.chunk_a.article_number} vs {p.chunk_b.article_number}</span>
                      <span className="text-sm text-textMuted">Сходство: {(p.scores.cosine * 100).toFixed(1)}%</span>
                    </div>
                    <p className="text-sm text-textMuted border-l-2 border-[#2d3748] pl-3">{p.chunk_a.text}</p>
                    <p className="text-sm text-textMuted border-l-2 border-blue-500/50 pl-3">{p.chunk_b.text}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Outdated */}
            <section>
              <h2 className="text-xl font-bold text-yellow-400 flex items-center gap-2 border-b border-[#2d3748] pb-2 mb-4">
                <HelpCircle size={20} /> Устаревшие нормы: {results.stats.outdated}
              </h2>
              <div className="space-y-4">
                {results.outdated.map((p: any, i: number) => (
                  <div key={i} className="bg-surface border border-yellow-500/30 rounded-xl p-4 space-y-3">
                    <div className="font-medium text-yellow-300 flex justify-between">
                      <span>{p.chunk_a.doc_title} ({p.chunk_a.article_number})</span>
                      <span className="text-sm text-textMuted">{(p.scores.cosine * 100).toFixed(1)}%</span>
                    </div>
                    <p className="text-sm bg-yellow-900/20 text-yellow-100/80 p-3 rounded">{p.chunk_a.text}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalAudit;
