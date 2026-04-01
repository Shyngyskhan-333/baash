import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
});

// No timeout for audit/index — can run for 10-30 minutes
const longApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 0,
});

export const searchDocuments = async (query: string, top_k = 10, docId?: string) => {
  const payload: Record<string, unknown> = { query, top_k };
  if (docId) payload.filters = { doc_id: docId };
  return (await api.post('/search', payload)).data;
};

export const analyzeDocument = async (docId: string) =>
  (await api.get(`/analyze/${docId}`)).data;

export const chatWithAi = async (
  message: string,
  history: { role: string; content: string }[],
  docId?: string,
  mode: 'general' | 'article_search' = 'general',
) =>
  (await api.post('/chat', {
    message,
    history: history.slice(-10), // keep last 10 to avoid huge payloads
    doc_id: docId ?? null,
    mode,
  })).data;

export const diffDocuments = async (textA: string, textB: string) =>
  (await api.post('/diff', { text_a: textA, text_b: textB })).data;

export const buildIndex = async (docIds: string[]) =>
  (await longApi.post('/index/build', { doc_ids: docIds })).data;

export const runGlobalAudit = async () =>
  (await longApi.post('/audit/detect')).data;

export const getHeatmapData = async () =>
  (await api.get('/graph/heatmap')).data;

export const getGraphHtmlUrl = (filterType = 'Все') =>
  `http://127.0.0.1:8000/api/v1/graph/html?filter_type=${encodeURIComponent(filterType)}`;

export const getAISettings = async () =>
  (await api.get('/settings/ai')).data;

export const saveAISettings = async (config: Record<string, unknown>) =>
  (await api.post('/settings/ai', config)).data;

export const testAIConnection = async (config: Record<string, unknown>) =>
  (await api.post('/settings/ai/test', config, { timeout: 30_000 })).data;

export const getOllamaModels = async () =>
  (await api.get('/settings/ollama/models', { timeout: 10_000 })).data;
