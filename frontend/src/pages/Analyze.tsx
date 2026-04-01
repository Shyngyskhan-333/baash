import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { analyzeDocument } from '../services/api';
import { ShieldCheck, AlertTriangle, ArrowLeft, ArrowRight, Loader2, ExternalLink } from 'lucide-react';

const AnalyzePage = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!docId) return;
    
    const fetchAnalysis = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await analyzeDocument(docId);
        setData(res);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Ошибка загрузки анализа');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnalysis();
  }, [docId]);

  if (!docId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-10 text-textMuted">
        <h2 className="text-2xl mb-4">Документ не выбран</h2>
        <button onClick={() => navigate('/')} className="text-primary hover:underline">Вернуться к поиску</button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="animate-spin text-primary" size={64} />
        <h2 className="text-xl font-medium tracking-wide">LexEntropy анализирует документ...</h2>
        <p className="text-textMuted">Нейросеть просматривает все статьи и ищет коллизии</p>
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

  if (!data) return null;

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
            <h1 className="text-3xl font-bold text-white leading-tight">{data.title}</h1>
            <a href={`https://adilet.zan.kz/rus/docs/${data.doc_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-primary hover:underline font-mono">
              <ExternalLink size={16} /> ID: {data.doc_id} на Adilet.zan.kz
            </a>
          </div>
          
          <div className={`shrink-0 flex flex-col items-center justify-center w-32 h-32 rounded-full border-4 bg-surface ${getRiskColor(data.risk_level)}`}>
            <span className="text-4xl font-extrabold">{Math.round(data.risk_score * 100)}</span>
            <span className="text-xs uppercase font-bold tracking-wider opacity-80 mt-1">
              Risk Score
            </span>
          </div>
        </div>

        <div className="bg-surface border border-[#2d3748] rounded-2xl p-6 shadow-xl">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Bot size={24} className="text-primary"/> AI Резюме (NLI + LLM)
          </h2>
          <p className="text-lg leading-relaxed text-textMain/90 font-medium">
            {data.summary}
          </p>
        </div>

        <div className="space-y-6">
          <h2 className="text-2xl font-bold border-b border-[#2d3748] pb-4">
            Выявленные проблемы ({data.issues.length})
          </h2>
          
          {data.issues.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 bg-surface/50 rounded-2xl border border-[#2d3748] text-center">
              <ShieldCheck size={64} className="text-riskLow mb-4 opacity-80" />
              <h3 className="text-xl font-medium text-white mb-2">Проблем не обнаружено</h3>
              <p className="text-textMuted">Закон не содержит коллизий и не ссылается на устаревшие нормы в рамках нашей базы.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {data.issues.map((issue: any, idx: number) => (
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
