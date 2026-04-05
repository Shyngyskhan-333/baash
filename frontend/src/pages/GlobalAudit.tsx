import { useState } from 'react';
import { runGlobalAudit } from '../services/api';
import { Search, AlertTriangle, FileWarning, HelpCircle, ShieldAlert, Zap } from 'lucide-react';
import { useStore } from '../store/useStore';

interface ChunkData {
  article_number: string;
  doc_title: string;
  text: string;
}

interface ProblemData {
  chunk_a: ChunkData;
  chunk_b: ChunkData;
  scores: { nli_confidence: number; cosine: number };
  explanation?: Record<string, unknown>;
}

const normalizeList = (value: unknown): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map(String).map(item => item.trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value.split(/[;,]\s*/).map(item => item.trim()).filter(Boolean);
  }
  return [String(value)];
};

const renderExplanation = (explanation?: Record<string, unknown>) => {
  if (!explanation) return null;
  const contradiction = explanation.contradiction ?? explanation.is_contradiction;
  const type = explanation.type ?? explanation.kind;
  const text = explanation.explanation ?? explanation.summary ?? explanation.reason ?? explanation.note;
  const articles = normalizeList(explanation.articles_involved ?? explanation.articles ?? explanation.sources);
  const fallback = JSON.stringify(explanation, null, 2);

  return (
    <div className="p-4 border-t border-border">
      <strong className="block mb-2 text-primary/60 text-[10px] font-mono uppercase tracking-wider">LLM</strong>
      <div className="rounded-lg bg-background border border-border p-3 text-xs text-textMuted space-y-2">
        {(typeof contradiction !== 'undefined' || typeof type !== 'undefined') && (
          <div className="flex flex-wrap gap-2">
            {typeof contradiction !== 'undefined' && (
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wide border ${
                contradiction ? 'border-riskHigh/30 text-riskHigh' : 'border-riskLow/30 text-riskLow'
              }`}>
                {contradiction ? 'Contradiction' : 'No conflict'}
              </span>
            )}
            {typeof type !== 'undefined' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wide border border-primary/20 text-primary/70">
                {String(type)}
              </span>
            )}
          </div>
        )}
        {typeof text === 'string' && text.trim().length > 0 && (
          <p className="leading-relaxed">{text}</p>
        )}
        {articles.length > 0 && (
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-textDim">Статьи</div>
            <div className="flex flex-col gap-1">
              {articles.map((item, idx) => (
                <span key={`${item}-${idx}`} className="text-[11px] text-textMuted">
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}
        {(!text || (typeof text === 'string' && text.trim().length === 0)) && articles.length === 0 && (
          <pre className="whitespace-pre-wrap font-mono text-[11px] text-textDim">{fallback}</pre>
        )}
      </div>
    </div>
  );
};

const GlobalAudit: React.FC = () => {
  const { auditResults, setAuditResults, auditLoading, setAuditLoading, activeScope } = useStore();
  const [error, setError] = useState<string | null>(null);

  const startAudit = async (forceRefresh = false) => {
    setAuditLoading(true);
    setError(null);
    try {
      const data = await runGlobalAudit(activeScope, forceRefresh);
      setAuditResults(data);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Ошибка при выполнении аудита.');
    } finally {
      setAuditLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-background grain">
      <div className="max-w-5xl mx-auto space-y-8 px-8 pt-28 pb-16 relative z-10">
        <header>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-riskHigh/10 border border-riskHigh/15 flex items-center justify-center">
              <ShieldAlert size={20} className="text-riskHigh" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-riskHigh to-riskMedium">
                Аудит коллизий
              </h1>
              <p className="text-textMuted text-sm">Детекция противоречий, дубликатов и устаревших норм.</p>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg px-4 py-2.5 inline-flex items-center gap-2 font-mono text-xs text-primary/70 mt-2">
            <Zap size={12} className="text-primary" />
            Top-10 FAISS → Cosine {'>'} 0.90 → Top-5 NLI → LLM JSON
          </div>
        </header>

        {activeScope.length > 0 && (
          <div className="flex items-center gap-2 bg-primary/5 border border-primary/10 rounded-lg px-4 py-2">
            <span className="text-[10px] text-primary font-mono uppercase tracking-wider font-bold">Scope</span>
            <div className="flex gap-1.5 flex-wrap">
              {activeScope.map((id) => (
                <span key={id} className="text-[10px] font-mono bg-primary/10 text-primary/80 px-2 py-0.5 rounded">
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={() => startAudit(false)}
            disabled={auditLoading}
            className={`flex items-center gap-2.5 px-6 py-3 rounded-xl font-bold text-sm transition font-display tracking-wide ${
              auditLoading
                ? 'bg-riskHigh/5 text-riskHighText/60 border border-riskHigh/15 cursor-not-allowed'
                : 'bg-riskHigh/10 text-riskHighText border border-riskHigh/20 hover:bg-riskHigh hover:text-surface hover:shadow-lg hover:shadow-riskHigh/20'
            }`}
          >
            {auditLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-riskHigh/20 border-t-riskHigh" /> Анализ O(N²)...
              </>
            ) : (
              <>
                <Search size={16} /> Запустить аудит
              </>
            )}
          </button>

          {auditResults && (
            <>
              {(auditResults as { cached?: boolean }).cached && (
                <span className="text-xs font-mono px-2 py-1 rounded border border-primary/20 bg-primary/5 text-primary/70">
                  CACHE
                </span>
              )}
              <button
                onClick={() => startAudit(true)}
                disabled={auditLoading}
                className="px-4 py-2 text-xs rounded-lg border border-border text-textMuted hover:text-textMain hover:bg-surfaceAlt transition disabled:opacity-40"
              >
                Пересчитать
              </button>
            </>
          )}
        </div>

        {error && <div className="text-riskHigh p-4 border border-riskHigh/20 rounded-lg bg-riskHigh/5 text-sm">{error}</div>}

        {auditResults && (
          <div className="space-y-10 animate-fade-up">
            <section>
              <h2 className="text-lg font-display font-bold text-riskHigh flex items-center gap-2 pb-3 border-b border-border mb-5">
                <AlertTriangle size={18} /> Противоречия: {auditResults.stats.contradictions}
              </h2>
              <div className="space-y-4">
                {auditResults.contradictions.map((problem, i: number) => {
                  const p = problem as unknown as ProblemData;
                  return (
                    <div key={i} className="bg-surface border border-riskHigh/15 rounded-xl overflow-hidden">
                      <div className="p-4 bg-riskHigh/[0.04] border-b border-riskHigh/10 font-display font-medium text-riskHighText/90 text-sm">
                        {p.chunk_a.article_number} vs {p.chunk_b.article_number}
                      </div>
                      <div className="p-4 grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <strong className="block text-primary/70 text-xs font-mono uppercase tracking-wider">{p.chunk_a.doc_title}</strong>
                          <p className="text-xs bg-background p-3 rounded-lg border border-border text-textMuted leading-relaxed">{p.chunk_a.text}</p>
                        </div>
                        <div className="space-y-2">
                          <strong className="block text-riskHigh/70 text-xs font-mono uppercase tracking-wider">{p.chunk_b.doc_title}</strong>
                          <p className="text-xs bg-riskHigh/[0.03] p-3 rounded-lg border border-riskHigh/10 text-textMuted leading-relaxed">{p.chunk_b.text}</p>
                        </div>
                      </div>
                      <div className="px-4 py-3 bg-surfaceAlt flex items-center text-xs font-mono text-textDim">
                        NLI: ~{(p.scores.nli_confidence * 100).toFixed(0)}%
                      </div>
                      {renderExplanation(p.explanation)}
                    </div>
                  );
                })}
              </div>
            </section>

            <section>
              <h2 className="text-lg font-display font-bold text-duplicate flex items-center gap-2 pb-3 border-b border-border mb-5">
                <FileWarning size={18} /> Дубликаты: {auditResults.stats.duplicates}
              </h2>
              <div className="space-y-4">
                {auditResults.duplicates.map((problem, i: number) => {
                  const p = problem as unknown as ProblemData;
                  return (
                    <div key={i} className="bg-surface border border-duplicate/15 rounded-xl p-4 space-y-3">
                      <div className="font-display font-medium text-duplicate/80 flex justify-between text-sm">
                        <span>{p.chunk_a.article_number} vs {p.chunk_b.article_number}</span>
                        <span className="text-xs text-textDim font-mono">Cosine: {(p.scores.cosine * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-xs text-textMuted border-l-2 border-border pl-3 leading-relaxed">{p.chunk_a.text}</p>
                      <p className="text-xs text-textMuted border-l-2 border-duplicate/30 pl-3 leading-relaxed">{p.chunk_b.text}</p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section>
              <h2 className="text-lg font-display font-bold text-outdated flex items-center gap-2 pb-3 border-b border-border mb-5">
                <HelpCircle size={18} /> Устаревшие: {auditResults.stats.outdated}
              </h2>
              <div className="space-y-4">
                {auditResults.outdated.map((problem, i: number) => {
                  const p = problem as unknown as ProblemData;
                  return (
                    <div key={i} className="bg-surface border border-outdated/15 rounded-xl p-4 space-y-3">
                      <div className="font-display font-medium text-outdated/80 flex justify-between text-sm">
                        <span>
                          {p.chunk_a.doc_title} ({p.chunk_a.article_number})
                        </span>
                        <span className="text-xs text-textDim font-mono">{(p.scores.cosine * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-xs bg-outdated/[0.04] text-textMuted p-3 rounded-lg border border-outdated/10 leading-relaxed">
                        {p.chunk_a.text}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalAudit;