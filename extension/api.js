import {
  DEFAULT_PROVIDER_SETTINGS,
  getProviderSettings,
  saveProviderSettings,
} from "./providerSettings.js";

export const Settings = { ...DEFAULT_PROVIDER_SETTINGS };

function isContextInvalidatedMessage(message) {
  const s = String(message || "").toLowerCase();
  return (
    s.includes("context invalidated")
    || s.includes("extension context")
    || s.includes("message port closed")
    || s.includes("receiving end does not exist")
  );
}

function toRuntimeError(message) {
  const normalizedMessage = String(message || "").trim();

  if (isContextInvalidatedMessage(normalizedMessage)) {
    const error = new Error(
      "Расширение обновилось. Обновите страницу (F5) и снова откройте панель LexLens.",
    );
    error.code = "EXTENSION_CONTEXT_INVALIDATED";
    return error;
  }

  const error = new Error(normalizedMessage || "Не удалось обменяться сообщениями с фоновым сервис-воркером.");
  error.code = "RUNTIME_ERROR";
  return error;
}

function applySettings(nextSettings) {
  Object.assign(Settings, nextSettings);
  return Settings;
}

export async function loadSettings() {
  return applySettings(await getProviderSettings());
}

export async function saveSettings(nextSettings) {
  return applySettings(await saveProviderSettings(nextSettings));
}

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
        const raw = response.error?.message || "Не удалось выполнить AI-запрос.";
        if (isContextInvalidatedMessage(raw)) {
          reject(toRuntimeError(raw));
          return;
        }
        const error = new Error(raw);
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

export function sendChatRequest(payload, channel = "chat") {
  return sendBackgroundMessage({
    type: "AI_PROVIDER_CHAT",
    channel,
    payload,
  });
}

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

export function testProviderConnection(channel = "settings-test") {
  return sendBackgroundMessage({
    type: "AI_TEST_PROVIDER",
    channel,
  });
}