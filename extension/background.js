import { ProviderError } from "./BaseProvider.js";
import { ProviderFactory } from "./ProviderFactory.js";
import { getProviderSettings } from "./providerSettings.js";
import {
  buildSelectionPipelineRequest,
  getSelectionPipelineMeta,
} from "./selectionPipelines.js";

const requestStateByChannel = new Map();

/**
 * Starts a tracked request for a logical UI channel.
 *
 * @param {string} channel
 * @param {number} timeoutMs
 * @returns {{ key: string, state: { controller: AbortController, reason: string|null, timeoutId: ReturnType<typeof setTimeout> } }}
 */
function beginTrackedRequest(channel, timeoutMs) {
  const key = channel || "default";
  const previousState = requestStateByChannel.get(key);

  if (previousState) {
    previousState.reason = "replaced";
    previousState.controller.abort();
  }

  const controller = new AbortController();
  const state = {
    controller,
    reason: null,
    timeoutId: null,
  };

  state.timeoutId = setTimeout(() => {
    state.reason = "timeout";
    controller.abort();
  }, timeoutMs);

  requestStateByChannel.set(key, state);
  return { key, state };
}

/**
 * Clears the tracked request state for a channel.
 *
 * @param {string} key
 * @param {{ controller: AbortController, reason: string|null, timeoutId: ReturnType<typeof setTimeout> }} state
 */
function finishTrackedRequest(key, state) {
  clearTimeout(state.timeoutId);

  if (requestStateByChannel.get(key) === state) {
    requestStateByChannel.delete(key);
  }
}

/**
 * Converts an abort into a stable ProviderError.
 *
 * @param {{ reason: string|null }} state
 * @param {string} providerName
 * @returns {ProviderError}
 */
function toAbortError(state, providerName) {
  if (state.reason === "timeout") {
    return new ProviderError("Превышен тайм-аут запроса к модели.", {
      code: "REQUEST_TIMEOUT",
      provider: providerName,
    });
  }

  if (state.reason === "replaced") {
    return new ProviderError("Предыдущий запрос отменён новым запросом.", {
      code: "REQUEST_CANCELLED",
      provider: providerName,
    });
  }

  if (state.reason === "cancelled") {
    return new ProviderError("Запрос отменён.", {
      code: "REQUEST_CANCELLED",
      provider: providerName,
    });
  }

  return new ProviderError("Запрос был прерван.", {
    code: "REQUEST_ABORTED",
    provider: providerName,
  });
}

/**
 * Converts any thrown error into a serializable response payload.
 *
 * @param {unknown} error
 * @returns {{ message: string, code: string, status: number|null, provider: string|null }}
 */
function serializeError(error) {
  if (error instanceof ProviderError) {
    return {
      message: error.message,
      code: error.code,
      status: error.status,
      provider: error.provider,
    };
  }

  return {
    message: error instanceof Error ? error.message : "Непредвиденная ошибка провайдера.",
    code: "UNEXPECTED_ERROR",
    status: null,
    provider: null,
  };
}

/**
 * Executes a provider request with storage-backed settings and timeout control.
 *
 * @param {string} channel
 * @param {object} payload
 * @returns {Promise<object>}
 */
async function executeProviderRequest(channel, payload) {
  const settings = await getProviderSettings();
  const provider = ProviderFactory.createProvider(settings);
  const { key, state } = beginTrackedRequest(channel, settings.requestTimeoutMs);

  try {
    return await provider.chat(payload, {
      signal: state.controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw toAbortError(state, provider.providerName);
    }

    throw error;
  } finally {
    finishTrackedRequest(key, state);
  }
}

/**
 * Handles a chat request from the UI.
 *
 * @param {object} message
 * @param {Function} sendResponse
 */
async function handleChatMessage(message, sendResponse) {
  try {
    const result = await executeProviderRequest(message.channel, message.payload || {});
    sendResponse({ ok: true, data: result });
  } catch (error) {
    sendResponse({ ok: false, error: serializeError(error) });
  }
}

/**
 * Handles a provider connectivity test from the UI.
 *
 * @param {object} message
 * @param {Function} sendResponse
 */
async function handleTestMessage(message, sendResponse) {
  try {
    const result = await executeProviderRequest(message.channel || "settings-test", {
      messages: [
        {
          role: "user",
          content: "Ответь одним словом: OK.",
        },
      ],
      temperature: 0,
      maxTokens: 2048,
    });

    sendResponse({
      ok: true,
      data: {
        ...result,
        status: "ok",
      },
    });
  } catch (error) {
    sendResponse({ ok: false, error: serializeError(error) });
  }
}

/**
 * Handles a predefined selection pipeline request from the UI.
 *
 * @param {object} message
 * @param {Function} sendResponse
 */
async function handleSelectionPipelineMessage(message, sendResponse) {
  try {
    const payload = buildSelectionPipelineRequest(
      message.pipeline,
      message.context || {},
    );
    const metadata = getSelectionPipelineMeta(message.pipeline);
    const result = await executeProviderRequest(
      message.channel || `selection:${message.pipeline}`,
      payload,
    );

    sendResponse({
      ok: true,
      data: {
        ...result,
        pipeline: message.pipeline,
        label: metadata.sidebarLabel,
      },
    });
  } catch (error) {
    sendResponse({ ok: false, error: serializeError(error) });
  }
}

/**
 * Cancels a tracked request channel if one exists.
 *
 * @param {object} message
 * @returns {{ ok: boolean, data: { cancelled: boolean } }}
 */
function handleCancelMessage(message) {
  const key = message.channel || "default";
  const state = requestStateByChannel.get(key);

  if (state) {
    state.reason = "cancelled";
    state.controller.abort();
  }

  return {
    ok: true,
    data: {
      cancelled: Boolean(state),
    },
  };
}

globalThis.chrome?.runtime?.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message?.type) {
    return undefined;
  }

  if (message.type === "AI_PROVIDER_CHAT") {
    handleChatMessage(message, sendResponse);
    return true;
  }

  if (message.type === "AI_TEST_PROVIDER") {
    handleTestMessage(message, sendResponse);
    return true;
  }

  if (message.type === "AI_SELECTION_PIPELINE") {
    handleSelectionPipelineMessage(message, sendResponse);
    return true;
  }

  if (message.type === "AI_CANCEL_REQUEST") {
    sendResponse(handleCancelMessage(message));
    return false;
  }

  return undefined;
});
