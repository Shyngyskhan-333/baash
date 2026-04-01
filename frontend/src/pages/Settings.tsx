import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Cpu, Cloud, Key, Server, CheckCircle, AlertTriangle, Loader2, ExternalLink, RefreshCw } from 'lucide-react';

const API = axios.create({ baseURL: 'http://127.0.0.1:8000/api/v1' });

const PROVIDERS = [
  {
    id: 'ollama',
    name: 'Локальный Qwen (Ollama)',
    icon: '🖥️',
    badge: 'БЕЗОПАСНО',
    badgeColor: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    desc: 'Данные не покидают сервер. Идеально для госсектора.',
    fields: ['ollama_url', 'ollama_model'],
    docUrl: 'https://ollama.com/download',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    icon: '🤖',
    badge: 'CLOUD',
    badgeColor: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    desc: 'GPT-4o, GPT-4 Turbo, GPT-3.5. Требует API ключ.',
    fields: ['api_key', 'model'],
    models: ['gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
    docUrl: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'azure',
    name: 'Azure OpenAI',
    icon: '☁️',
    badge: 'ENTERPRISE',
    badgeColor: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
    desc: 'Azure OpenAI с частным эндпоинтом. Для корпоративных клиентов.',
    fields: ['api_key', 'endpoint', 'model'],
    docUrl: 'https://portal.azure.com',
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    icon: '⚡',
    badge: 'CLOUD',
    badgeColor: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    desc: 'Claude 3.5 Sonnet, Claude 3 Haiku. Отличный для анализа документов.',
    fields: ['api_key', 'model'],
    models: ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
    docUrl: 'https://console.anthropic.com/',
  },
];

export default function SettingsPage() {
  const [current, setCurrent] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [selectedProvider, setSelectedProvider] = useState('ollama');
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaRunning, setOllamaRunning] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    API.get('/settings/ai').then(r => {
      setCurrent(r.data);
      setForm(r.data);
      setSelectedProvider(r.data.provider || 'ollama');
    });
    API.get('/settings/ollama/models').then(r => {
      setOllamaModels(r.data.models || []);
      setOllamaRunning(r.data.running || false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await API.post('/settings/ai', { ...form, provider: selectedProvider });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await API.post('/settings/ai/test', { ...form, provider: selectedProvider });
      setTestResult({ ok: true, msg: resp.data });
    } catch (e: any) {
      setTestResult({ ok: false, msg: e.response?.data?.detail || e.message });
    } finally {
      setTesting(false);
    }
  };

  const refreshOllama = async () => {
    const r = await API.get('/settings/ollama/models');
    setOllamaModels(r.data.models || []);
    setOllamaRunning(r.data.running || false);
  };

  const prov = PROVIDERS.find(p => p.id === selectedProvider);

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-background">
      <div className="max-w-3xl mx-auto space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-extrabold flex items-center gap-3 mb-2">
            <Settings className="text-indigo-400" size={32} />
            Настройки AI-провайдера
          </h1>
          <p className="text-textMuted">
            Выберите AI-провайдер. Для госсектора рекомендуем <strong className="text-emerald-400">локальный Qwen</strong> — данные остаются на вашем сервере.
          </p>
        </div>

        {/* Provider Cards */}
        <div className="grid grid-cols-2 gap-3">
          {PROVIDERS.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedProvider(p.id)}
              className={`glass rounded-xl p-4 text-left transition-all border ${
                selectedProvider === p.id
                  ? 'border-indigo-500/60 bg-indigo-500/5'
                  : 'border-white/5 hover:border-white/15'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{p.icon}</span>
                <span className="font-semibold text-sm text-textMain">{p.name}</span>
                <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full border ${p.badgeColor}`}>{p.badge}</span>
              </div>
              <p className="text-xs text-textMuted leading-relaxed">{p.desc}</p>
            </button>
          ))}
        </div>

        {/* Config Form */}
        {prov && (
          <div className="glass rounded-2xl p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-lg flex items-center gap-2">
                <span className="text-2xl">{prov.icon}</span> {prov.name}
              </h2>
              <a
                href={prov.docUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-indigo-400 hover:underline flex items-center gap-1"
              >
                <ExternalLink size={12} /> Документация
              </a>
            </div>

            {/* Ollama special block */}
            {selectedProvider === 'ollama' && (
              <div className={`rounded-xl p-4 border ${ollamaRunning ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-yellow-500/5 border-yellow-500/20'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Server size={16} className={ollamaRunning ? 'text-emerald-400' : 'text-yellow-400'} />
                  <span className="text-sm font-semibold">
                    Ollama: {ollamaRunning ? '🟢 Запущен' : '🔴 Не найден'}
                  </span>
                  <button onClick={refreshOllama} className="ml-auto text-textMuted hover:text-white">
                    <RefreshCw size={14} />
                  </button>
                </div>
                {!ollamaRunning && (
                  <div className="text-xs text-yellow-300 space-y-1">
                    <p>Установите Ollama и запустите модель:</p>
                    <code className="block bg-black/30 p-2 rounded font-mono text-xs mt-1">
                      ollama pull qwen2.5:7b<br/>
                      ollama serve
                    </code>
                  </div>
                )}
                {ollamaRunning && ollamaModels.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-textMuted mb-2">Установленные модели:</p>
                    <div className="flex flex-wrap gap-2">
                      {ollamaModels.map(m => (
                        <button
                          key={m}
                          onClick={() => setForm((f: any) => ({ ...f, ollama_model: m }))}
                          className={`text-xs px-2 py-1 rounded-full border transition ${form.ollama_model === m ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' : 'border-white/10 bg-white/5 text-textMuted hover:bg-white/10'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Fields */}
            {prov.fields.map(field => {
              if (field === 'api_key') return (
                <div key={field}>
                  <label className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2 flex items-center gap-1.5">
                    <Key size={12} /> API Ключ
                  </label>
                  <input
                    type="password"
                    placeholder="sk-... или ваш ключ"
                    value={form.api_key || ''}
                    onChange={e => setForm((f: any) => ({ ...f, api_key: e.target.value }))}
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-textMain outline-none focus:border-indigo-500/50 transition font-mono"
                  />
                </div>
              );
              if (field === 'endpoint') return (
                <div key={field}>
                  <label className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2 block">Azure Endpoint URL</label>
                  <input
                    type="text"
                    placeholder="https://your-resource.openai.azure.com/"
                    value={form.endpoint || ''}
                    onChange={e => setForm((f: any) => ({ ...f, endpoint: e.target.value }))}
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-textMain outline-none focus:border-indigo-500/50 transition font-mono"
                  />
                </div>
              );
              if (field === 'model') return (
                <div key={field}>
                  <label className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2 block">
                    {selectedProvider === 'azure' ? 'Deployment Name' : 'Модель'}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder={selectedProvider === 'azure' ? 'gpt-4o (ваш deployment name)' : 'gpt-4o'}
                      value={form.model || ''}
                      onChange={e => setForm((f: any) => ({ ...f, model: e.target.value }))}
                      className="flex-1 bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-textMain outline-none focus:border-indigo-500/50 transition font-mono"
                    />
                  </div>
                  {prov.models && (
                    <div className="flex gap-2 mt-2 flex-wrap">
                      {prov.models.map(m => (
                        <button
                          key={m}
                          onClick={() => setForm((f: any) => ({ ...f, model: m }))}
                          className={`text-xs px-2 py-1 rounded-full border transition ${form.model === m ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300' : 'border-white/10 bg-white/5 text-textMuted hover:bg-white/10'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
              if (field === 'ollama_url') return (
                <div key={field}>
                  <label className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2 block">Ollama URL</label>
                  <input
                    type="text"
                    value={form.ollama_url || 'http://localhost:11434'}
                    onChange={e => setForm((f: any) => ({ ...f, ollama_url: e.target.value }))}
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-textMain outline-none focus:border-indigo-500/50 transition font-mono"
                  />
                </div>
              );
              if (field === 'ollama_model') return (
                <div key={field}>
                  <label className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2 block">Модель Ollama</label>
                  <input
                    type="text"
                    placeholder="qwen2.5:7b"
                    value={form.ollama_model || 'qwen2.5:7b'}
                    onChange={e => setForm((f: any) => ({ ...f, ollama_model: e.target.value }))}
                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-textMain outline-none focus:border-indigo-500/50 transition font-mono"
                  />
                  <p className="text-xs text-textMuted mt-1">Популярные: <code>qwen2.5:7b</code>, <code>qwen3:14b</code>, <code>llama3.2:3b</code>, <code>mistral:7b</code></p>
                </div>
              );
              return null;
            })}

            {/* Test result */}
            {testResult && (
              <div className={`rounded-xl p-4 text-sm border ${testResult.ok ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300' : 'bg-red-500/5 border-red-500/20 text-red-300'}`}>
                <div className="flex items-center gap-2 font-semibold mb-1">
                  {testResult.ok ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                  {testResult.ok ? 'Подключение успешно!' : 'Ошибка подключения'}
                </div>
                {testResult.ok && testResult.msg?.available_models && (
                  <p className="text-xs opacity-80">Доступные модели: {testResult.msg.available_models.join(', ')}</p>
                )}
                {!testResult.ok && <p className="text-xs opacity-80">{String(testResult.msg)}</p>}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleTest}
                disabled={testing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-sm font-medium transition"
              >
                {testing ? <Loader2 size={15} className="animate-spin" /> : <Cpu size={15} />}
                Тест соединения
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition"
              >
                {saving ? <Loader2 size={15} className="animate-spin" /> : saved ? <CheckCircle size={15} /> : <Cloud size={15} />}
                {saved ? 'Сохранено!' : 'Сохранить'}
              </button>
            </div>
          </div>
        )}

        {/* Qwen Guide */}
        {selectedProvider === 'ollama' && (
          <div className="glass rounded-2xl p-6 border border-emerald-500/10">
            <h3 className="font-bold text-emerald-400 mb-3 flex items-center gap-2"><Server size={18}/> Быстрый старт — Qwen 7B локально</h3>
            <ol className="space-y-3 text-sm text-textMuted">
              <li className="flex gap-3"><span className="text-emerald-400 font-bold shrink-0">1.</span>
                <span>Скачайте <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">Ollama для Windows</a> и установите</span>
              </li>
              <li className="flex gap-3"><span className="text-emerald-400 font-bold shrink-0">2.</span>
                <span>В терминале выполните: <code className="bg-black/30 px-2 py-0.5 rounded text-emerald-300">ollama pull qwen2.5:7b</code> (скачает ~4.5 GB)</span>
              </li>
              <li className="flex gap-3"><span className="text-emerald-400 font-bold shrink-0">3.</span>
                <span>Ollama запускается автоматически. Нажмите «Тест соединения» выше.</span>
              </li>
              <li className="flex gap-3"><span className="text-emerald-400 font-bold shrink-0">4.</span>
                <span>Выберите <code className="bg-black/30 px-2 py-0.5 rounded text-emerald-300">qwen2.5:7b</code> из появившихся моделей и жмите «Сохранить».</span>
              </li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
