import axios from 'axios';

const QUICK_TEST_UI = ['1', 'true', 'yes', 'on'].includes(
  String(
    import.meta.env.VITE_QUICK_TEST_MODE ?? import.meta.env.VITE_DEMO_MODE ?? '',
  ).toLowerCase(),
);

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
});

const longApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 0,
});

export const searchDocuments = async (query: string, top_k = 10, docId?: string, docIds?: string[]) => {
  const payload: Record<string, unknown> = { query, top_k };
  if (docId) payload.filters = { doc_id: docId };
  if (docIds && docIds.length > 0) payload.doc_ids = docIds;
  return (await api.post('/search', payload)).data;
};

export const analyzeDocument = async (docId: string, docIds?: string[], forceRefresh = false) => {
  const params = docIds && docIds.length > 0 ? `?doc_ids=${docIds.join('&doc_ids=')}` : '';
  const refreshParam = forceRefresh ? `${params ? '&' : '?'}force_refresh=true` : '';
  return (await api.get(`/analyze/${docId}${params}${refreshParam}`)).data;
};

export const chatWithAi = async (
  message: string,
  history: { role: string; content: string }[],
  docId?: string,
  mode: 'general' | 'article_search' = 'general',
  docIds?: string[],
) =>
  (await api.post('/chat', {
    message,
    history: history.slice(-10),
    doc_id: docId ?? null,
    doc_ids: docIds ?? null,
    mode,
  })).data;

export const diffDocuments = async (textA: string, textB: string) =>
  (await api.post('/diff', { text_a: textA, text_b: textB })).data;

export const buildIndex = async (docIds: string[]) =>
  (await longApi.post('/index/build', { doc_ids: docIds })).data;

export const previewDocument = async (docId: string) =>
  (await api.get(`/index/preview/${docId}`)).data;

export const fetchDocument = async (docId: string) =>
  (await api.get(`/index/document/${docId}`)).data;

export const fetchDocumentByUrl = async (url: string) =>
  (await api.get(`/index/document/by-url`, { params: { url } })).data;

export const runGlobalAudit = async (docIds?: string[], forceRefresh = false) => {
  const payload: Record<string, unknown> = {};
  if (docIds && docIds.length > 0) payload.doc_ids = docIds;
  if (forceRefresh) payload.force_refresh = true;
  return (await longApi.post('/audit/detect', payload)).data;
};

export const getHeatmapData = async (docIds?: string[]) => {
  const params = docIds && docIds.length > 0 ? `?doc_ids=${docIds.join(',')}` : '';
  const qtParam = QUICK_TEST_UI ? `${params ? '&' : '?'}quicktest=1` : '';
  return (await api.get(`/graph/heatmap${params}${qtParam}`)).data;
};

export const getGraphHtmlUrl = (filterType = '\u0412\u0441\u0435', docIds?: string[]) => {
  const scopeParam = docIds && docIds.length > 0 ? `&doc_ids=${docIds.join(',')}` : '';
  const qtParam = QUICK_TEST_UI ? '&quicktest=1' : '';
  return `http://127.0.0.1:8000/api/v1/graph/html?filter_type=${encodeURIComponent(filterType)}${scopeParam}${qtParam}`;
};

export const getAISettings = async () =>
  (await api.get('/settings/ai')).data;

export const saveAISettings = async (config: Record<string, unknown>) =>
  (await api.post('/settings/ai', config)).data;

export const testAIConnection = async (config: Record<string, unknown>) =>
  (await api.post('/settings/ai/test', config, { timeout: 30_000 })).data;

export const getOllamaModels = async () =>
  (await api.get('/settings/ollama/models', { timeout: 10_000 })).data;

export const precomputeAll = async (docIds?: string[]) => {
  const payload: Record<string, unknown> = {};
  if (docIds && docIds.length > 0) payload.doc_ids = docIds;
  return (await api.post('/precompute/all', payload)).data;
};