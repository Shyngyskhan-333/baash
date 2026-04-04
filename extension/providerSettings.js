export const SUPPORTED_PROVIDER_NAMES = Object.freeze(["azure", "ollama"]);

export const DEFAULT_PROVIDER_SETTINGS = Object.freeze({
  provider: "ollama",
  azureApiKey: "",
  azureEndpointUrl: "",
  azureResourceName: "",
  azureDeploymentName: "",
  azureApiVersion: "2024-02-01",
  ollamaBaseUrl: "http://localhost:11434",
  ollamaModel: "llama3.1",
  requestTimeoutMs: 45000,
});

export const PROVIDER_STORAGE_KEYS = Object.keys(DEFAULT_PROVIDER_SETTINGS);

/**
 * Normalizes a provider label into a supported internal key when possible.
 *
 * @param {string} provider
 * @returns {string}
 */
export function normalizeProviderName(provider) {
  const value = String(provider || "").trim().toLowerCase();

  if (["azure", "azure-openai", "azure openai"].includes(value)) {
    return "azure";
  }

  if (["ollama", "local", "local ollama", "olama"].includes(value)) {
    return "ollama";
  }

  return value;
}

/**
 * Returns the display name for a provider key.
 *
 * @param {string} provider
 * @returns {string}
 */
export function getProviderLabel(provider) {
  return normalizeProviderName(provider) === "azure" ? "Azure OpenAI" : "Ollama";
}

/**
 * Converts a saved Azure value into a canonical endpoint URL when possible.
 *
 * @param {string} value
 * @returns {string}
 */
export function normalizeAzureEndpointUrl(value) {
  const rawValue = String(value || "").trim().replace(/\/+$/, "");
  if (!rawValue) {
    return "";
  }

  if (/^https?:\/\//i.test(rawValue)) {
    return rawValue;
  }

  if (rawValue.includes(".")) {
    return `https://${rawValue}`;
  }

  return `https://${rawValue}.openai.azure.com`;
}

/**
 * Extracts the Azure resource name from a canonical endpoint URL.
 *
 * @param {string} endpointUrl
 * @returns {string}
 */
export function deriveAzureResourceName(endpointUrl) {
  const normalizedUrl = normalizeAzureEndpointUrl(endpointUrl);
  if (!normalizedUrl) {
    return "";
  }

  try {
    const host = new URL(normalizedUrl).host;
    return host.replace(/\.openai\.azure\.com$/i, "");
  } catch {
    return normalizedUrl
      .replace(/^https?:\/\//i, "")
      .replace(/\/.*$/, "")
      .replace(/\.openai\.azure\.com$/i, "");
  }
}

/**
 * Merges arbitrary values into the default provider settings.
 *
 * @param {object} settings
 * @returns {object}
 */
export function normalizeProviderSettings(settings = {}) {
  const provider = normalizeProviderName(
    settings.provider ?? DEFAULT_PROVIDER_SETTINGS.provider,
  );
  const timeoutValue = Number(settings.requestTimeoutMs);
  const azureEndpointUrl = normalizeAzureEndpointUrl(
    settings.azureEndpointUrl || settings.azureResourceName,
  );

  return {
    ...DEFAULT_PROVIDER_SETTINGS,
    ...settings,
    provider: SUPPORTED_PROVIDER_NAMES.includes(provider)
      ? provider
      : DEFAULT_PROVIDER_SETTINGS.provider,
    azureApiKey: String(
      settings.azureApiKey ?? DEFAULT_PROVIDER_SETTINGS.azureApiKey,
    ).trim(),
    azureEndpointUrl,
    azureResourceName:
      deriveAzureResourceName(azureEndpointUrl) ||
      String(
        settings.azureResourceName ?? DEFAULT_PROVIDER_SETTINGS.azureResourceName,
      ).trim(),
    azureDeploymentName: String(
      settings.azureDeploymentName ?? DEFAULT_PROVIDER_SETTINGS.azureDeploymentName,
    ).trim(),
    azureApiVersion: String(
      settings.azureApiVersion ?? DEFAULT_PROVIDER_SETTINGS.azureApiVersion,
    ).trim(),
    ollamaBaseUrl: String(
      settings.ollamaBaseUrl ?? DEFAULT_PROVIDER_SETTINGS.ollamaBaseUrl,
    )
      .trim()
      .replace(/\/+$/, ""),
    ollamaModel: String(
      settings.ollamaModel ?? DEFAULT_PROVIDER_SETTINGS.ollamaModel,
    ).trim(),
    requestTimeoutMs:
      Number.isFinite(timeoutValue) && timeoutValue >= 5000
        ? timeoutValue
        : DEFAULT_PROVIDER_SETTINGS.requestTimeoutMs,
  };
}

/**
 * Returns the required setup fields for a provider.
 *
 * @param {object} settings
 * @returns {Array<object>}
 */
export function getProviderRequirements(settings = {}) {
  const normalized = normalizeProviderSettings(settings);

  if (normalized.provider === "azure") {
    return [
      {
        key: "endpoint",
        label: "Адрес API",
        detail: "Адрес API Azure OpenAI",
        present: Boolean(normalized.azureEndpointUrl),
        value: normalized.azureEndpointUrl,
      },
      {
        key: "model",
        label: "Модель / Deployment",
        detail: "Имя deployment в Azure",
        present: Boolean(normalized.azureDeploymentName),
        value: normalized.azureDeploymentName,
      },
      {
        key: "credential",
        label: "API-ключ",
        detail: "Значение заголовка api-key",
        present: Boolean(normalized.azureApiKey),
        value: normalized.azureApiKey ? "настроен" : "",
      },
    ];
  }

  return [
    {
      key: "endpoint",
      label: "Адрес API",
      detail: "Локальный адрес API Ollama",
      present: Boolean(normalized.ollamaBaseUrl),
      value: normalized.ollamaBaseUrl,
    },
    {
      key: "model",
      label: "Модель",
      detail: "Имя локально установленной модели",
      present: Boolean(normalized.ollamaModel),
      value: normalized.ollamaModel,
    },
  ];
}

/**
 * Computes a UI-friendly readiness summary for the active provider.
 *
 * @param {object} settings
 * @returns {object}
 */
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

/**
 * Loads the persisted provider settings from chrome.storage.local.
 *
 * @returns {Promise<object>}
 */
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

/**
 * Persists provider settings to chrome.storage.local.
 *
 * @param {object} nextSettings
 * @returns {Promise<object>}
 */
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
