import {
  DEFAULT_PROVIDER_SETTINGS,
  getProviderSettings,
  saveProviderSettings,
} from "./providerSettings.js";

export const Settings = { ...DEFAULT_PROVIDER_SETTINGS };

/**
 * Converts runtime failures into clearer UI-facing errors.
 *
 * @param {string} message
 * @returns {Error}
 */
function toRuntimeError(message) {
  const normalizedMessage = String(message || "").trim();

  if (/Extension context invalidated/i.test(normalizedMessage)) {
    const error = new Error(
      "Расширение было перезагружено. Обновите страницу, снова откройте LexLens и повторите попытку.",
    );
    error.code = "EXTENSION_CONTEXT_INVALIDATED";
    return error;
  }

  const error = new Error(normalizedMessage || "Не удалось обменяться сообщениями с фоновым сервис-воркером.");
  error.code = "RUNTIME_ERROR";
  return error;
}

/**
 * Copies the latest settings into the shared in-memory state.
 *
 * @param {object} nextSettings
 * @returns {object}
 */
function applySettings(nextSettings) {
  Object.assign(Settings, nextSettings);
  return Settings;
}

/**
 * Loads provider settings from chrome.storage.local.
 *
 * @returns {Promise<object>}
 */
export async function loadSettings() {
  return applySettings(await getProviderSettings());
}

/**
 * Saves provider settings to chrome.storage.local.
 *
 * @param {object} nextSettings
 * @returns {Promise<object>}
 */
export async function saveSettings(nextSettings) {
  return applySettings(await saveProviderSettings(nextSettings));
}

/**
 * Sends a message to the background service worker and unwraps the result.
 *
 * @param {object} message
 * @returns {Promise<object>}
 */
export function sendBackgroundMessage(message) {
  return new Promise((resolve, reject) => {
    const runtime = globalThis.chrome?.runtime;
    if (!runtime?.sendMessage) {
      reject(
        toRuntimeError("chrome.runtime.sendMessage недоступен. Перезагрузите страницу расширения."),
      );
      return;
    }

    runtime.sendMessage(message, (response) => {
      const runtimeError = globalThis.chrome?.runtime?.lastError;
      if (runtimeError) {
        reject(toRuntimeError(runtimeError.message));
        return;
      }

      if (!response) {
        reject(new Error("Нет ответа от фонового сервис-воркера."));
        return;
      }

      if (!response.ok) {
        const error = new Error(response.error?.message || "Не удалось выполнить AI-запрос.");
        error.code = response.error?.code;
        error.status = response.error?.status;
        error.provider = response.error?.provider;
        reject(error);
        return;
      }

      resolve(response.data);
    });
  });
}

/**
 * Sends a chat request to the selected provider through the service worker.
 *
 * @param {object} payload
 * @param {string} [channel="chat"]
 * @returns {Promise<object>}
 */
export function sendChatRequest(payload, channel = "chat") {
  return sendBackgroundMessage({
    type: "AI_PROVIDER_CHAT",
    channel,
    payload,
  });
}

/**
 * Runs a predefined selection pipeline through the service worker.
 *
 * @param {string} pipeline
 * @param {object} context
 * @param {string} [channel="selection-action"]
 * @returns {Promise<object>}
 */
export function sendSelectionPipelineRequest(
  pipeline,
  context,
  channel = "selection-action",
) {
  return sendBackgroundMessage({
    type: "AI_SELECTION_PIPELINE",
    channel,
    pipeline,
    context,
  });
}

/**
 * Runs a lightweight connectivity test for the selected provider.
 *
 * @param {string} [channel="settings-test"]
 * @returns {Promise<object>}
 */
export function testProviderConnection(channel = "settings-test") {
  return sendBackgroundMessage({
    type: "AI_TEST_PROVIDER",
    channel,
  });
}
