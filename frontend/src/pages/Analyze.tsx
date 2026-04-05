import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { analyzeDocument } from '../services/api';
import { useStore } from '../store/useStore';
import { AlertTriangle, ArrowLeft, Loader2, ExternalLink, Check, ChevronDown, ChevronUp, BrainCircuit, Bot } from 'lucide-react';

const AnalyzePage = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const { activeScope, analysisResult, setAnalysisResult, setSelectedDocId } = useStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);
  const [isFullOpen, setIsFullOpen] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);

  const runAnalysis = useCallback(async (forceRefresh = false) => {
    if (!docId) return;
    setLoading(true);
    setError('');
    try {
      const res = await analyzeDocument(docId, activeScope, forceRefresh);
      setAnalysisResult(res);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Ошибка загрузки анализа');
    } finally {
      setLoading(false);
    }
  }, [activeScope, docId, setAnalysisResult]);

  useEffect(() => {
    if (!docId) return;
    setSelectedDocId(docId);
    if (analysisResult && analysisResult.doc_id === docId) return;
    runAnalysis();
  }, [activeScope, analysisResult, docId, runAnalysis, setSelectedDocId]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (loading) {
      interval = setInterval(() => { setLoadingStep(prev => prev >= 4 ? prev : prev + 1); }, 1500);
    } else {
      setLoadingStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  if (!docId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-10 text-textMuted">
        <h2 className="text-2xl font-display mb-4">Документ не выбран</h2>
        <button onClick={() => navigate('/')} className="text-primary hover:underline">Вернуться к поиску</button>
      </div>
    );
  }

  if (loading) {
    const steps = [
      'Загрузка текста НПА...',
      'Сбор структуры статей и внутренних ссылок...',
      'Подготовка фрагмента для модели...',
      'Глубокий смысловой разбор (LLM)...',
      'Секции: предмет, адресаты, практика, вывод...',
    ];

    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-8 bg-background relative overflow-hidden grain">
        <div className="relative flex items-center justify-center w-28 h-28 z-10">
          <div className="absolute inset-0 rounded-full border-2 border-primary/10 border-t-primary animate-spin" />
          <div className="absolute inset-3 rounded-full border-2 border-riskMedium/10 border-b-riskMedium animate-[spin_2.5s_linear_infinite_reverse]" />
          <div className="absolute inset-6 rounded-full border-2 border-riskLow/10 border-r-riskLow animate-[spin_3s_linear_infinite]" />
          <BrainCircuit className="text-primary animate-pulse w-8 h-8" />
        </div>

        <div className="text-center space-y-5 max-w-md w-full z-10">
          <h2 className="text-2xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-primaryStrong">
            Нейросетевой анализ
          </h2>

          <div className="bg-surface/80 backdrop-blur border border-primary/15 rounded-2xl p-6 text-left font-mono text-[13px] shadow-2xl relative overflow-hidden flex flex-col gap-3">
            <div className="absolute top-0 left-0 w-0.5 h-full bg-gradient-to-b from-primary via-riskMedium to-riskLow animate-glow-pulse" />
            {steps.map((step, idx) => (
              <div key={idx} className={`flex items-center gap-3 transition-all duration-500 ${
                idx === loadingStep ? 'text-textMain opacity-100 translate-x-1' :
                idx < loadingStep ? 'text-primary/60 opacity-70' :
                'text-textDim opacity-30'
              }`}>
                <div className="w-5 flex justify-center shrink-0">
                  {idx < loadingStep ? <Check size={14} className="text-riskLow" /> :
                   idx === loadingStep ? <Loader2 size={13} className="animate-spin text-primary" /> :
                   <div className="w-1 h-1 rounded-full bg-textDim" />}
                </div>
                <span className={idx === loadingStep ? 'font-semibold' : ''}>{step}</span>
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
        <div className="bg-riskHigh/5 text-riskHigh p-8 rounded-2xl max-w-lg text-center border border-riskHigh/20">
          <AlertTriangle size={48} className="mx-auto mb-4 opacity-70" />
          <h2 className="text-xl font-display font-bold mb-2">Ошибка анализа</h2>
          <p className="text-riskHigh/80">{error}</p>
          <button onClick={() => navigate('/')} className="mt-6 px-5 py-2.5 bg-riskHigh text-surface rounded-lg font-bold transition hover:bg-primaryStrong">Назад</button>
        </div>
      </div>
    );
  }

  if (!analysisResult) return null;

  const sectionLabels: Record<string, string> = {
    subject: 'Предмет и цели',
    scope: 'Кому применимо',
    practice: 'Практика применения',
    duties: 'Права, обязанности и ограничения',
    structure: 'Структура и логика текста',
    related: 'Связанные области/акты',
    conclusion: 'Вывод',
  };

  const analysisExtras = analysisResult as { summary_short?: string; sections?: Record<string, string> };
  const summaryShort = analysisExtras.summary_short || analysisResult.summary;
  const sections = analysisExtras.sections || {};

  return (
    <div className="flex-1 overflow-auto bg-background grain">
      <div className="max-w-5xl mx-auto space-y-8 px-10 pt-28 pb-16 relative z-10">

        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-textMuted hover:text-primary transition font-mono text-sm">
          <ArrowLeft size={16} /> поиск
        </button>

        <div className="space-y-3">
          <h1 className="text-3xl font-display font-bold text-textMain leading-tight">{analysisResult.title}</h1>
          <a
            href={`https://adilet.zan.kz/rus/docs/${analysisResult.doc_id}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 text-primary/70 hover:text-primary font-mono text-sm transition"
          >
            <ExternalLink size={14} /> {analysisResult.doc_id}
          </a>
          <button
            onClick={() => runAnalysis(true)}
            className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-textSub hover:text-primary text-xs font-mono transition"
            type="button"
          >
            Обновить анализ
          </button>
          <p className="text-xs text-textMuted max-w-2xl mt-3 leading-relaxed">
            Здесь только смысловой разбор текста акта. Дубликаты, противоречия и пересечения с другими НПА — в разделах{' '}
            <span className="text-textSub">«Глобальный аудит»</span> и <span className="text-textSub">«Граф»</span>.
          </p>
        </div>

        {analysisResult.reasoning && (
          <div className="bg-surface border border-border rounded-2xl overflow-hidden transition-all">
            <div className="flex items-center justify-between cursor-pointer group p-5" onClick={() => setIsReasoningOpen(!isReasoningOpen)}>
              <h2 className="text-base font-display font-semibold flex items-center gap-2 text-textMuted group-hover:text-textSub transition">
                <BrainCircuit size={18} className="text-primary/60" /> Процесс размышления
              </h2>
              {isReasoningOpen ? <ChevronUp size={18} className="text-textDim" /> : <ChevronDown size={18} className="text-textDim" />}
            </div>
            {isReasoningOpen && (
              <div className="px-5 pb-5">
                <div className="divider-amber mb-4" />
                <div className="bg-background rounded-xl p-5 text-textMuted font-mono text-sm leading-relaxed whitespace-pre-wrap max-h-[400px] overflow-y-auto border border-border/50">
                  {analysisResult.reasoning}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-display font-semibold flex items-center gap-2 text-textSub">
            <Bot size={18} className="text-primary" /> {'Ключевые нормы и смысл'}
          </h2>
          <p className="text-lg leading-relaxed text-textMain/90 font-medium">{summaryShort}</p>

          <button
            onClick={() => setIsFullOpen(!isFullOpen)}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-textSub hover:text-primary text-xs font-mono transition"
            type="button"
          >
            {isFullOpen ? 'Свернуть подробное объяснение' : 'Показать полное объяснение'}
          </button>

          {isFullOpen && (
            <div className="pt-2 space-y-4">
              {Object.keys(sections).length > 0 ? (
                Object.entries(sections).map(([key, value]) => (
                  <div key={key} className="bg-background rounded-xl p-4 border border-border/50">
                    <h3 className="text-sm font-semibold text-textSub mb-2">
                      {sectionLabels[key] || key}
                    </h3>
                    <p className="text-sm leading-relaxed text-textMain/90 whitespace-pre-wrap">{String(value)}</p>
                  </div>
                ))
              ) : (
                <div className="bg-background rounded-xl p-4 border border-border/50">
                  <p className="text-sm leading-relaxed text-textMain/90 whitespace-pre-wrap">{analysisResult.summary}</p>
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default AnalyzePage;