export const SUPPORTED_PROVIDER_NAMES = Object.freeze(["azure", "ollama", "openai"]);

export const DEFAULT_PROVIDER_SETTINGS = Object.freeze({
  provider: "ollama",
  azureApiKey: "",
  azureEndpointUrl: "",
  azureResourceName: "",
  azureDeploymentName: "",
  azureApiVersion: "2024-02-01",
  openaiApiKey: "",
  openaiBaseUrl: "https://api.openai.com/v1",
  openaiModel: "",
  ollamaBaseUrl: "http://localhost:11434",
  ollamaModel: "llama3.1",
  requestTimeoutMs: 60000,
});

export const PROVIDER_STORAGE_KEYS = Object.keys(DEFAULT_PROVIDER_SETTINGS);

export function normalizeProviderName(provider) {
  const value = String(provider || "").trim().toLowerCase();

  if (["azure", "azure-openai", "azure openai"].includes(value)) return "azure";
  if (["openai", "open ai", "open-ai", "gpt"].includes(value)) return "openai";
  if (["ollama", "local", "local ollama", "olama"].includes(value)) return "ollama";

  return value;
}

export function getProviderLabel(provider) {
  const normalized = normalizeProviderName(provider);
  if (normalized === "azure") return "Azure OpenAI";
  if (normalized === "openai") return "OpenAI";
  return "Ollama";
}

export function normalizeAzureEndpointUrl(value) {
  const rawValue = String(value || "").trim().replace(/\/+$/, "");
  if (!rawValue) return "";
  if (/^https?:\/\//i.test(rawValue)) return rawValue;
  if (rawValue.includes(".")) return `https://${rawValue}`;
  return `https://${rawValue}.openai.azure.com`;
}

export function deriveAzureResourceName(endpointUrl) {
  const normalizedUrl = normalizeAzureEndpointUrl(endpointUrl);
  if (!normalizedUrl) return "";

  try {
    const host = new URL(normalizedUrl).host;
    return host.replace(/\.openai\.azure\.com$/i, "");
  } catch {
    return normalizedUrl.replace(/^https?:\/\//i, "").replace(/\/.*$/, "").replace(/\.openai\.azure\.com$/i, "");
  }
}

export function normalizeProviderSettings(settings = {}) {
  const provider = normalizeProviderName(settings.provider ?? DEFAULT_PROVIDER_SETTINGS.provider);
  const timeoutValue = Number(settings.requestTimeoutMs);
  const azureEndpointUrl = normalizeAzureEndpointUrl(settings.azureEndpointUrl || settings.azureResourceName);

  return {
    ...DEFAULT_PROVIDER_SETTINGS,
    ...settings,
    provider: SUPPORTED_PROVIDER_NAMES.includes(provider) ? provider : DEFAULT_PROVIDER_SETTINGS.provider,
    azureApiKey: String(settings.azureApiKey ?? DEFAULT_PROVIDER_SETTINGS.azureApiKey).trim(),
    azureEndpointUrl,
    azureResourceName: deriveAzureResourceName(azureEndpointUrl) || String(settings.azureResourceName ?? DEFAULT_PROVIDER_SETTINGS.azureResourceName).trim(),
    azureDeploymentName: String(settings.azureDeploymentName ?? DEFAULT_PROVIDER_SETTINGS.azureDeploymentName).trim(),
    azureApiVersion: String(settings.azureApiVersion ?? DEFAULT_PROVIDER_SETTINGS.azureApiVersion).trim(),
    openaiApiKey: String(settings.openaiApiKey ?? DEFAULT_PROVIDER_SETTINGS.openaiApiKey).trim(),
    openaiBaseUrl: String(settings.openaiBaseUrl ?? DEFAULT_PROVIDER_SETTINGS.openaiBaseUrl).trim().replace(/\/+$/, ""),
    openaiModel: String(settings.openaiModel ?? DEFAULT_PROVIDER_SETTINGS.openaiModel).trim(),
    ollamaBaseUrl: String(settings.ollamaBaseUrl ?? DEFAULT_PROVIDER_SETTINGS.ollamaBaseUrl).trim().replace(/\/+$/, ""),
    ollamaModel: String(settings.ollamaModel ?? DEFAULT_PROVIDER_SETTINGS.ollamaModel).trim(),
    requestTimeoutMs: Number.isFinite(timeoutValue) && timeoutValue >= 5000 ? timeoutValue : DEFAULT_PROVIDER_SETTINGS.requestTimeoutMs,
  };
}

export function getProviderRequirements(settings = {}) {
  const normalized = normalizeProviderSettings(settings);

  if (normalized.provider === "azure") {
    return [
      { key: "endpoint", label: "Адрес API", detail: "Адрес Azure OpenAI endpoint", present: Boolean(normalized.azureEndpointUrl), value: normalized.azureEndpointUrl },
      { key: "model", label: "Deployment", detail: "Имя deployment в Azure", present: Boolean(normalized.azureDeploymentName), value: normalized.azureDeploymentName },
      { key: "credential", label: "API-ключ", detail: "Ключ доступа Azure OpenAI", present: Boolean(normalized.azureApiKey), value: normalized.azureApiKey ? "настроен" : "" },
    ];
  }

  if (normalized.provider === "openai") {
    return [
      { key: "endpoint", label: "Адрес API", detail: "Базовый URL OpenAI API", present: Boolean(normalized.openaiBaseUrl), value: normalized.openaiBaseUrl },
      { key: "model", label: "Модель", detail: "Имя модели OpenAI", present: Boolean(normalized.openaiModel), value: normalized.openaiModel },
      { key: "credential", label: "API-ключ", detail: "Bearer token OpenAI", present: Boolean(normalized.openaiApiKey), value: normalized.openaiApiKey ? "настроен" : "" },
    ];
  }

  return [
    { key: "endpoint", label: "Адрес API", detail: "Локальный адрес Ollama", present: Boolean(normalized.ollamaBaseUrl), value: normalized.ollamaBaseUrl },
    { key: "model", label: "Модель", detail: "Имя локальной модели", present: Boolean(normalized.ollamaModel), value: normalized.ollamaModel },
  ];
}

export function getProviderReadiness(settings = {}) {
  const normalized = normalizeProviderSettings(settings);
  const requirements = getProviderRequirements(normalized);
  const missingRequirements = requirements.filter((item) => !item.present);

  return {
    provider: normalized.provider,
    providerLabel: getProviderLabel(normalized.provider),
    settings: normalized,
    requirements,
    missingRequirements,
    detectedCount: requirements.length - missingRequirements.length,
    totalCount: requirements.length,
    isConfigured: missingRequirements.length === 0,
  };
}

export function getProviderSettings() {
  return new Promise((resolve, reject) => {
    const storageArea = globalThis.chrome?.storage?.local;
    if (!storageArea) {
      reject(new Error("chrome.storage.local недоступен."));
      return;
    }

    storageArea.get(PROVIDER_STORAGE_KEYS, (storedValues) => {
      const runtimeError = globalThis.chrome?.runtime?.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }

      resolve(normalizeProviderSettings(storedValues));
    });
  });
}

export async function saveProviderSettings(nextSettings) {
  const mergedSettings = normalizeProviderSettings({
    ...(await getProviderSettings()),
    ...nextSettings,
  });

  return new Promise((resolve, reject) => {
    const storageArea = globalThis.chrome?.storage?.local;
    if (!storageArea) {
      reject(new Error("chrome.storage.local недоступен."));
      return;
    }

    storageArea.set(mergedSettings, () => {
      const runtimeError = globalThis.chrome?.runtime?.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }

      resolve(mergedSettings);
    });
  });
}