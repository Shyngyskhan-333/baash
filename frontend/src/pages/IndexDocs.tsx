import React, { useState } from 'react';
import { DownloadCloud, Server, CheckCircle2 } from 'lucide-react';
import { buildIndex } from '../services/api';

const IndexDocs: React.FC = () => {
  const [docIds, setDocIds] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIndex = async () => {
    if (!docIds.trim()) {
      setError("Введите хотя бы один ID документа.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    const ids = docIds.split(',').map(id => id.trim()).filter(id => id);

    try {
      const res = await buildIndex(ids);
      setResult(res);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Ошибка индексации документов");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-background">
      <div className="max-w-4xl mx-auto space-y-8 px-8 pt-28 pb-16">
        <header>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400 mb-2">
            Индексация НПА (Adilet)
          </h1>
          <p className="text-textMuted text-lg">
            Данные скачиваются, разбиваются на иерархию и превращаются в легковесные эмбеддинги e5-small.
          </p>
        </header>

        <div className="bg-surface border border-[#2d3748] rounded-xl p-6 space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-textMain" htmlFor="docIds">
              Введите ID документа (через запятую):
            </label>
            <input
              id="docIds"
              type="text"
              placeholder="например: K1500000377, K1400000266"
              className="w-full bg-[#1a202c] border border-[#2d3748] rounded px-4 py-3 focus:outline-none focus:border-indigo-500 transition"
              value={docIds}
              onChange={(e) => setDocIds(e.target.value)}
            />
          </div>

          <div className="flex gap-4 items-center">
            <button
              onClick={handleIndex}
              disabled={loading}
              className={`flex items-center gap-2 px-6 py-3 rounded font-medium transition ${
                loading ? 'bg-indigo-600/50 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
              } text-white`}
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Загрузка, парсинг и векторизация...
                </div>
              ) : (
                <>
                  <DownloadCloud size={18} />
                  --build-index
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="p-4 bg-red-900/20 border border-red-500/50 rounded text-red-400 flex items-start gap-3">
              <Server size={20} className="shrink-0 mt-0.5" />
              <div>
                <strong className="block mb-1">Ошибка:</strong>
                {error}
              </div>
            </div>
          )}

          {result && (
            <div className="p-4 bg-green-900/20 border border-green-500/50 rounded text-green-400 flex items-start gap-3">
              <CheckCircle2 size={20} className="shrink-0 mt-0.5" />
              <div>
                <strong className="block mb-1">Успех:</strong>
                Успешно обработано: {result.added_chunks} чанков (статей/пунктов).
                <br />
                {result.message && <span className="opacity-80">{result.message}</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IndexDocs;
