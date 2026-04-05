import { ProviderError } from "./BaseProvider.js";
import { ProviderFactory } from "./ProviderFactory.js";
import { getProviderSettings } from "./providerSettings.js";
import {
  buildSelectionPipelineRequest,
  getSelectionPipelineMeta,
} from "./selectionPipelines.js";

const requestStateByChannel = new Map();
const LOCAL_BACKEND_BASE = "http://127.0.0.1:8000/api/v1";

async function fetchRelatedNpaByCosine(context) {
  const selectionText = String(context?.text || "").trim();
  if (!selectionText) {
    throw new ProviderError("      .", {
      code: "MISSING_SELECTION",
      provider: "local-backend",
    });
  }

  const response = await fetch(`${LOCAL_BACKEND_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: selectionText.slice(0, 1200),
      top_k: 5,
    }),
  });

  if (!response.ok) {
    throw new ProviderError("  .   FastAPI  127.0.0.1:8000.", {
      code: "BACKEND_UNAVAILABLE",
      status: response.status,
      provider: "local-backend",
    });
  }

  const data = await response.json();
  const results = Array.isArray(data?.results) ? data.results : [];

  if (results.length === 0) {
    return {
      answer: "По выделенному фрагменту в локальном индексе ничего не найдено.",
    };
  }

  const searchSnippet = selectionText.replace(/\s+/g, " ").trim().slice(0, 120);

  const relatedItems = results.map((item, index) => {
    const score = item.cosine_score ?? item.score ?? 0;
    const docId = item.doc_id || "";
    const searchParam = searchSnippet ? `?search=${encodeURIComponent(searchSnippet)}` : "";
    const url = docId ? `https://adilet.zan.kz/rus/docs/${docId}${searchParam}` : "";
    return {
      index: index + 1,
      title: item.title || "Без названия",
      docId,
      score,
      url,
    };
  });

  return {
    answer: "Подобраны документы по смысловой близости к выделенному тексту.",
    relatedItems,
  };
}

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

function finishTrackedRequest(key, state) {
  clearTimeout(state.timeoutId);

  if (requestStateByChannel.get(key) === state) {
    requestStateByChannel.delete(key);
  }
}

function toAbortError(state, providerName) {
  if (state.reason === "timeout") {
    return new ProviderError(" -   .", {
      code: "REQUEST_TIMEOUT",
      provider: providerName,
    });
  }

  if (state.reason === "replaced") {
    return new ProviderError("    .", {
      code: "REQUEST_CANCELLED",
      provider: providerName,
    });
  }

  if (state.reason === "cancelled") {
    return new ProviderError(" .", {
      code: "REQUEST_CANCELLED",
      provider: providerName,
    });
  }

  return new ProviderError("  .", {
    code: "REQUEST_ABORTED",
    provider: providerName,
  });
}

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
    message: error instanceof Error ? error.message : "  .",
    code: "UNEXPECTED_ERROR",
    status: null,
    provider: null,
  };
}

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

async function handleChatMessage(message, sendResponse) {
  try {
    const result = await executeProviderRequest(message.channel, message.payload || {});
    sendResponse({ ok: true, data: result });
  } catch (error) {
    sendResponse({ ok: false, error: serializeError(error) });
  }
}

async function handleTestMessage(message, sendResponse) {
  try {
    const result = await executeProviderRequest(message.channel || "settings-test", {
      messages: [
        {
          role: "user",
          content: "  : OK.",
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

async function handleSelectionPipelineMessage(message, sendResponse) {
  try {
    const metadata = getSelectionPipelineMeta(message.pipeline);
    if (message.pipeline === "find_related_npa" || message.pipeline === "find_articles_by_topic") {
      const related = await fetchRelatedNpaByCosine(message.context || {});
      sendResponse({
        ok: true,
        data: {
          ...related,
          pipeline: message.pipeline,
          label: metadata.sidebarLabel,
        },
      });
      return;
    }

    const payload = buildSelectionPipelineRequest(
      message.pipeline,
      message.context || {},
    );
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