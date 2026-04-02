import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { analyzeDocument, buildIndex } from '../services/api';
import { useStore } from '../store/useStore';
import { ShieldCheck, AlertTriangle, ArrowLeft, ArrowRight, Loader2, ExternalLink, Plus, Check, ChevronDown, ChevronUp, BrainCircuit } from 'lucide-react';

const AnalyzePage = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const { activeScope, setActiveScope, analysisResult, setAnalysisResult, setSelectedDocId } = useStore();

  const [loading, setLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState('');
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);

  useEffect(() => {
    if (!docId) return;
    setSelectedDocId(docId);
    
    // Only fetch if we don't have results for THIS specific docId

    if (analysisResult && analysisResult.doc_id === docId) {
      return;
    }

    const fetchAnalysis = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await analyzeDocument(docId, activeScope);
        setAnalysisResult(res);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Ошибка загрузки анализа');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnalysis();
  }, [docId, activeScope, analysisResult, setAnalysisResult]);

  const handleAddToScope = async () => {
    if (!docId || activeScope.includes(docId)) return;
    setIsAdding(true);
    try {
      await buildIndex([docId]);
      setActiveScope([...activeScope, docId]);
    } catch (err) {
      console.error("Failed to add to scope:", err);
    } finally {
      setIsAdding(false);
    }
  };

  const [loadingStep, setLoadingStep] = useState(0);

  useEffect(() => {
    let interval: any;
    if (loading) {
      interval = setInterval(() => {
         setLoadingStep(prev => {
           if (prev >= 5) return prev; // stop at last
           return prev + 1;
         });
      }, 1500);
    } else {
      setLoadingStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  if (!docId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-10 text-textMuted">
        <h2 className="text-2xl mb-4">Документ не выбран</h2>
        <button onClick={() => navigate('/')} className="text-primary hover:underline">Вернуться к поиску</button>
      </div>
    );
  }

  if (loading) {
    const steps = [
      "Инициализация пайплайна NLP...",
      "Разбивка текста на смысловые фрагменты (chunking)...",
      "Генерация векторов (multilingual-e5-base)...",
      "Семантический поиск (FAISS + BM25)...",
      "Проверка на коллизии (DeBERTa NLI)...",
      "Агрегация и финальный вывод (LLM)..."
    ];

    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-8 bg-background relative overflow-hidden">
        {/* Decorative Grid Background */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTMwLjUgMjEuNWw5LTE1bDEwIDE1djMwbS0xOS0zMGwtOS0xNWwtMTAgMTV2MzBtMTkgMHAxMHpNMzAgMHY2MG0wLTMwaDMwbS0zMCAwaDMwIiBzdHJva2U9IiMzMzMiIHN0cm9rZS13aWR0aD0iMC41IiBmaWxsPSJub25lIiBvcGFjaXR5PSIwLjMiLz48L3N2Zz4=')] opacity-20" />
        
        <div className="relative flex items-center justify-center w-32 h-32 z-10 scale-110">
          <div className="absolute inset-0 rounded-full border-[3px] border-primary/10 border-t-primary animate-spin shadow-[0_0_20px_rgba(99,102,241,0.5)]"></div>
          <div className="absolute inset-3 rounded-full border-[3px] border-[#f59e0b]/10 border-b-[#f59e0b] animate-[spin_2.5s_linear_infinite_reverse]"></div>
          <div className="absolute inset-6 rounded-full border-[3px] border-[#10b981]/10 border-r-[#10b981] animate-[spin_3s_linear_infinite]"></div>
          <BrainCircuit className="text-white animate-pulse w-10 h-10 filter drop-shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
        </div>
        
        <div className="text-center space-y-5 max-w-md w-full z-10">
          <h2 className="text-2xl font-extrabold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-primary to-indigo-300">
            Нейросетевой анализ...
          </h2>
          
          <div className="bg-surface/80 backdrop-blur border border-indigo-500/30 rounded-2xl p-6 text-left font-mono text-[13px] shadow-2xl relative overflow-hidden flex flex-col gap-3">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary via-[#f59e0b] to-[#10b981] animate-pulse"></div>
            {steps.map((step, idx) => (
              <div key={idx} className={`flex items-center gap-3 transition-all duration-500 ${idx === loadingStep ? 'text-white opacity-100 transform translate-x-2' : idx < loadingStep ? 'text-primary opacity-70' : 'text-textMuted opacity-30'}`}>
                <div className="w-5 flex justify-center shrink-0">
                  {idx < loadingStep ? <Check size={16} className="text-riskLow" /> : idx === loadingStep ? <Loader2 size={14} className="animate-spin text-[#f59e0b]" /> : <div className="w-1.5 h-1.5 rounded-full bg-textMuted" />}
                </div>
                <span className={`${idx === loadingStep ? 'font-bold' : ''} tracking-tight`}>{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-10">
        <div className="bg-riskHigh bg-opacity-10 text-riskHigh p-6 rounded-2xl max-w-lg text-center border border-[#ef4444]">
          <AlertTriangle size={48} className="mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Ошибка анализа</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/')} className="mt-6 px-4 py-2 bg-[#ef4444] text-white rounded-lg hover:bg-opacity-80 transition">Назад</button>
        </div>
      </div>
    );
  }

  if (!analysisResult) return null;

  const getRiskColor = (level: string) => {
    switch(level) {
      case 'low': return 'text-riskLow border-riskLow shadow-[0_0_15px_rgba(34,197,94,0.3)]';
      case 'medium': return 'text-riskMedium border-riskMedium shadow-[0_0_15px_rgba(245,158,11,0.3)]';
      case 'high': return 'text-riskHigh border-riskHigh shadow-[0_0_15px_rgba(239,68,68,0.3)]';
      default: return 'text-textMuted border-[#2d3748]';
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-background">
      <div className="max-w-5xl mx-auto space-y-8 px-10 pt-28 pb-16">
        
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-textMuted hover:text-white transition">
          <ArrowLeft size={20} /> Вернуться к поиску
        </button>

        <div className="flex items-start justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-white leading-tight">{analysisResult.title}</h1>
            <a href={`https://adilet.zan.kz/rus/docs/${analysisResult.doc_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-primary hover:underline font-mono">
              <ExternalLink size={16} /> ID: {analysisResult.doc_id} на Adilet.zan.kz
            </a>
          </div>

          <div className="flex gap-4 items-start translate-y-2">
            {!activeScope.includes(analysisResult.doc_id) ? (
              <button
                onClick={handleAddToScope}
                disabled={isAdding}
                className="flex items-center gap-2 px-4 py-2.5 bg-primary/10 border border-primary/30 text-primary rounded-xl hover:bg-primary/20 transition-all font-medium whitespace-nowrap shadow-lg shadow-primary/5"
              >
                {isAdding ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                Добавить в область
              </button>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-riskLow/10 border border-riskLow/30 text-riskLow rounded-xl font-medium whitespace-nowrap">
                <Check size={16} /> В области
              </div>
            )}
            
            <div className={`shrink-0 flex flex-col items-center justify-center w-24 h-24 rounded-full border-4 bg-surface ${getRiskColor(analysisResult.risk_level)}`}>
              <span className="text-3xl font-extrabold">{Math.round(analysisResult.risk_score * 100)}</span>
              <span className="text-[10px] uppercase font-bold tracking-wider opacity-80 mt-0.5">
                Risk
              </span>
            </div>
          </div>
        </div>

        {analysisResult.reasoning && (
          <div className="bg-surface border border-[#2d3748] rounded-2xl p-6 shadow-xl transition-all">
            <div 
              className="flex items-center justify-between cursor-pointer group"
              onClick={() => setIsReasoningOpen(!isReasoningOpen)}
            >
              <h2 className="text-xl font-semibold flex items-center gap-2 text-textMuted group-hover:text-white transition-colors">
                <BrainCircuit size={24} className="text-textMuted group-hover:text-primary transition-colors"/> 
                Процесс размышления (LLM)
              </h2>
              <button className="text-textMuted group-hover:text-primary transition-colors">
                {isReasoningOpen ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
              </button>
            </div>
            
            {isReasoningOpen && (
              <div className="mt-4 pt-4 border-t border-[#2d3748]">
                <div className="bg-background/50 rounded-xl p-5 text-textMuted font-mono text-sm leading-relaxed whitespace-pre-wrap max-h-[400px] overflow-y-auto">
                  {analysisResult.reasoning}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="bg-surface border border-[#2d3748] rounded-2xl p-6 shadow-xl">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Bot size={24} className="text-primary"/> AI Резюме (NLI + LLM)
          </h2>
          <p className="text-lg leading-relaxed text-textMain/90 font-medium">
            {analysisResult.summary}
          </p>
        </div>

        <div className="space-y-6">
          <h2 className="text-2xl font-bold border-b border-[#2d3748] pb-4">
            Выявленные проблемы ({analysisResult.issues.length})
          </h2>
          
          {analysisResult.issues.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 bg-surface/50 rounded-2xl border border-[#2d3748] text-center">
              <ShieldCheck size={64} className="text-riskLow mb-4 opacity-80" />
              <h3 className="text-xl font-medium text-white mb-2">Проблем не обнаружено</h3>
              <p className="text-textMuted">Закон не содержит коллизий и не ссылается на устаревшие нормы в рамках нашей базы.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {analysisResult.issues.map((issue: any, idx: number) => (
                <div key={idx} className={`bg-surface p-6 rounded-xl border-l-4 shadow-lg flex flex-col gap-3 ${issue.severity === 'high' ? 'border-riskHigh' : issue.severity === 'medium' ? 'border-riskMedium' : 'border-riskLow'}`}>
                  <div className="flex justify-between items-start">
                    <span className="font-mono bg-[#2d3748] text-white px-3 py-1 rounded text-sm tracking-wide">
                      {issue.article}
                    </span>
                    <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded bg-opacity-10 ${issue.severity === 'high' ? 'bg-riskHigh text-riskHigh' : issue.severity === 'medium' ? 'bg-riskMedium text-riskMedium' : 'bg-riskLow text-riskLow'}`}>
                      {issue.type === 'contradiction' ? 'Коллизия' : issue.type === 'duplicate' ? 'Дубликат' : 'Устаревшее'}
                    </span>
                  </div>
                  <p className="text-lg font-medium">{issue.description}</p>
                  
                  {issue.explanation && (
                    <div className="mt-2 text-sm text-textMuted bg-[#2d3748]/50 p-4 rounded-lg">
                      <strong className="text-white/80 block mb-1">AI Объяснение:</strong>
                      {issue.explanation}
                    </div>
                  )}
                  
                  {issue.related_doc_id && (
                    <button onClick={() => navigate(`/analyze/${issue.related_doc_id}`)} className="self-start text-sm text-primary hover:underline flex items-center gap-1 mt-2">
                       Перейти к связанному акту ({issue.related_doc_id}) <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

// Simple Mock Bot Icon
const Bot = ({ size, className }: { size: number, className: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
);

export default AnalyzePage;
