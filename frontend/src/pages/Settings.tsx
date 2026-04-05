import { useEffect, useState } from 'react';
import { Bot, CheckCircle2, Loader2, RefreshCcw, Save, Server, Zap } from 'lucide-react';
import { getAISettings, getOllamaModels, precomputeAll, saveAISettings, testAIConnection } from '../services/api';

type AIConfig = {
  provider: string;
  azure_endpoint: string;
  azure_key: string;
  azure_deployment: string;
  azure_api_version: string;
  openai_key: string;
  openai_model: string;
  anthropic_key: string;
  anthropic_model: string;
  ollama_url: string;
  ollama_model: string;
};

const DEFAULT_CONFIG: AIConfig = {
  provider: 'mock',
  azure_endpoint: '',
  azure_key: '',
  azure_deployment: 'gpt-4o',
  azure_api_version: '2024-02-15-preview',
  openai_key: '',
  openai_model: 'gpt-4o-mini',
  anthropic_key: '',
  anthropic_model: 'claude-3-5-sonnet-latest',
  ollama_url: 'http://localhost:11434',
  ollama_model: 'qwen2.5:7b',
};

const SettingsPage = () => {
  const [config, setConfig] = useState<AIConfig>(DEFAULT_CONFIG);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [precomputing, setPrecomputing] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAISettings();
        setConfig({ ...DEFAULT_CONFIG, ...(data.config || {}) });
      } catch {
        setMessageType('error');
        setMessage('Не удалось загрузить настройки AI.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const update = (key: keyof AIConfig, value: string) => {
    setConfig((current) => ({ ...current, [key]: value }));
  };

  const refreshOllamaModels = async () => {
    try {
      const data = await getOllamaModels();
      setModels(data.models || []);
      if (data.status === 'error') {
        setMessageType('error');
        setMessage(data.message || 'Ollama недоступен.');
      }
    } catch {
      setMessageType('error');
      setMessage('Не удалось получить список моделей Ollama.');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await saveAISettings(config);
      setMessageType('success');
      setMessage(data.message || 'Настройки сохранены.');
    } catch {
      setMessageType('error');
      setMessage('Не удалось сохранить настройки.');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const data = await testAIConnection(config);
      setMessageType(data.status === 'ok' ? 'success' : 'error');
      setMessage(data.message || 'Проверка завершена.');
    } catch {
      setMessageType('error');
      setMessage('Проверка соединения завершилась ошибкой.');
    } finally {
      setTesting(false);
    }
  };

  const handlePrecompute = async () => {
    setPrecomputing(true);
    setMessageType('info');
    setMessage('Прогрев запущен. Это может занять несколько минут...');
    try {
      const data = await precomputeAll();
      setMessageType('success');
      setMessage(
        `Готово: документов ${data.doc_ids_count}, анализов ${data.analyze_cached}, аудит ${data.audit_cached ? 'ok' : 'нет'}, граф ${data.graph_cached ? 'ok' : 'нет'}.`
      );
    } catch {
      setMessageType('error');
      setMessage('Не удалось выполнить прогрев.');
    } finally {
      setPrecomputing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={28} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto bg-background grain">
      <div className="max-w-4xl mx-auto px-8 pt-28 pb-16 space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-primary/10 border border-primary/15 flex items-center justify-center">
            <Server className="text-primary" size={20} />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold text-textMain">Настройки AI</h1>
            <p className="text-textMuted text-sm">Конфигурация провайдера для чата, diff, explain и аудита.</p>
          </div>
        </div>

        {message && (
          <div className={`rounded-xl border px-4 py-3 text-sm ${
            messageType === 'success'
              ? 'bg-riskLow/10 border-riskLow/20 text-riskLowText'
              : messageType === 'error'
                ? 'bg-riskHigh/10 border-riskHigh/20 text-riskHighText'
                : 'bg-surface border-border text-textSub'
          }`}>
            {message}
          </div>
        )}

        <div className="bg-surface border border-border rounded-2xl p-6 space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-mono uppercase tracking-wider text-textMuted">Провайдер</label>
            <select
              value={config.provider}
              onChange={(event) => update('provider', event.target.value)}
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none"
            >
              <option value="azure">Azure OpenAI</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama</option>
              <option value="mock">Mock</option>
            </select>
          </div>

          {config.provider === 'azure' && (
            <>
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Azure endpoint" value={config.azure_endpoint} onChange={(event) => update('azure_endpoint', event.target.value)} />
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="API ключ" value={config.azure_key} onChange={(event) => update('azure_key', event.target.value)} />
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Deployment" value={config.azure_deployment} onChange={(event) => update('azure_deployment', event.target.value)} />
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Версия API (например 2024-02-15-preview)" value={config.azure_api_version} onChange={(event) => update('azure_api_version', event.target.value)} />
            </>
          )}

          {config.provider === 'openai' && (
            <div className="space-y-3">
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="API ключ" value={config.openai_key} onChange={(event) => update('openai_key', event.target.value)} />
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Модель (например gpt-4o-mini)" value={config.openai_model} onChange={(event) => update('openai_model', event.target.value)} />
            </div>
          )}

          {config.provider === 'anthropic' && (
            <div className="space-y-3">
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="API ключ" value={config.anthropic_key} onChange={(event) => update('anthropic_key', event.target.value)} />
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Модель (например claude-3-5-sonnet-latest)" value={config.anthropic_model} onChange={(event) => update('anthropic_model', event.target.value)} />
            </div>
          )}

          {config.provider === 'ollama' && (
            <div className="space-y-3">
              <input className="w-full bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Ollama URL" value={config.ollama_url} onChange={(event) => update('ollama_url', event.target.value)} />
              <div className="flex gap-3">
                <input className="flex-1 bg-background border border-border rounded-xl px-4 py-3 text-textMain outline-none" placeholder="Модель Ollama" value={config.ollama_model} onChange={(event) => update('ollama_model', event.target.value)} />
                <button onClick={refreshOllamaModels} className="px-4 py-3 rounded-xl border border-border text-textSub hover:text-primary transition">
                  <RefreshCcw size={16} />
                </button>
              </div>
              {models.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {models.map((model) => (
                    <button key={model} onClick={() => update('ollama_model', model)} className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-mono">
                      {model}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button onClick={handleSave} disabled={saving} className="px-5 py-3 rounded-xl bg-primary text-surface font-bold flex items-center gap-2 disabled:opacity-50">
              {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
              Сохранить
            </button>
            <button onClick={handleTest} disabled={testing} className="px-5 py-3 rounded-xl border border-border text-textSub hover:text-primary flex items-center gap-2 disabled:opacity-50">
              {testing ? <Loader2 className="animate-spin" size={16} /> : <CheckCircle2 size={16} />}
              Проверить подключение
            </button>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 text-textSub mb-2">
            <Bot size={16} className="text-primary" />
            <span className="font-display font-semibold">Поведение в рантайме</span>
          </div>
          <p className="text-sm text-textMuted leading-relaxed">
            Эти настройки используются backend‑провайдером напрямую, поэтому chat, diff и explain работают через выбранный источник без перезапуска сервера.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 text-textSub mb-2">
            <Zap size={16} className="text-primary" />
            <span className="font-display font-semibold">Прогрев кэшей</span>
          </div>
          <p className="text-sm text-textMuted leading-relaxed mb-4">
            Запускает полный прогрев анализа, аудита и графов, чтобы интерфейс открывался быстрее.
          </p>
          <button
            onClick={handlePrecompute}
            disabled={precomputing}
            className="px-5 py-3 rounded-xl border border-border text-textSub hover:text-primary flex items-center gap-2 disabled:opacity-50"
          >
            {precomputing ? <Loader2 className="animate-spin" size={16} /> : <Zap size={16} />}
            Прогреть всё
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;