import { BaseProvider, ProviderError } from "./BaseProvider.js";

/**
 * Strategy implementation for local Ollama chat requests.
 */
export class OllamaProvider extends BaseProvider {
  /**
   * Returns the provider key.
   *
   * @returns {string}
   */
  get providerName() {
    return "ollama";
  }

  /**
   * Validates the Ollama configuration from storage.
   */
  validateConfig() {
    if (!this.config.ollamaModel) {
      throw new ProviderError("Для Ollama не заполнено поле ollamaModel.", {
        code: "OLLAMA_CONFIG_ERROR",
        provider: this.providerName,
      });
    }
  }

  /**
   * Builds the Ollama local endpoint.
   *
   * @returns {string}
   */
  getRequestUrl() {
    const rawUrl = String(this.config.ollamaBaseUrl || "http://localhost:11434").trim();

    // If the user provided a full /api/chat path, use it as-is
    if (rawUrl.toLowerCase().includes("/api/chat")) {
      return rawUrl;
    }

    return `${rawUrl.replace(/\/+$/, "")}/api/chat`;
  }

  /**
   * Builds the Ollama chat body.
   *
   * @param {object} payload
   * @returns {object}
   */
  buildRequestBody(payload) {
    const body = {
      model: this.config.ollamaModel,
      messages: payload.messages,
      stream: false,
      options: {
        ...(payload.options || {}),
      },
    };

    // Map common extension parameters to Ollama's 'options' sub-object
    if (Number.isInteger(payload.maxTokens)) {
      body.options.num_predict = payload.maxTokens;
    }

    if (typeof payload.temperature === "number") {
      body.options.temperature = payload.temperature;
    }

    if (typeof payload.keepAlive === "string") {
      body.keep_alive = payload.keepAlive;
    }

    return body;
  }

  /**
   * Extracts the assistant message from the Ollama response.
   *
   * @param {object|string|null} data
   * @returns {object}
   */
  parseResponse(data) {
    const answer = this.normalizeMessageContent(data?.message?.content);
    if (!answer) {
      throw new ProviderError("Ollama вернул пустой ответ.", {
        code: "OLLAMA_EMPTY_RESPONSE",
        provider: this.providerName,
        details: data,
      });
    }

    return {
      answer,
      provider: this.providerName,
      raw: data,
    };
  }

  /**
   * Maps Ollama HTTP failures to stable UI errors.
   *
   * @param {Response} response
   * @param {object|string|null} data
   * @returns {ProviderError}
   */
  buildHttpError(response, data) {
    if (response.status === 404) {
      return new ProviderError(
        "Endpoint Ollama не найден. Убедитесь, что локальный сервер запущен на http://localhost:11434.",
        {
          code: "OLLAMA_ENDPOINT_NOT_FOUND",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    if (response.status === 429) {
      return new ProviderError(
        "Для Ollama достигнут лимит запросов (429). Повторите попытку позже.",
        {
          code: "OLLAMA_RATE_LIMITED",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    return new ProviderError(
      this.extractErrorMessage(data) ||
        `Запрос к Ollama завершился ошибкой со статусом ${response.status}.`,
      {
        code: "OLLAMA_HTTP_ERROR",
        status: response.status,
        provider: this.providerName,
        details: data,
      },
    );
  }

  /**
   * Maps fetch failures to the required "server offline" error.
   *
   * @param {Error} error
   * @returns {ProviderError}
   */
  buildNetworkError(error) {
    const errorText = String(error?.message || "").toLowerCase();
    const isOfflineError = errorText.includes("fetch") || errorText.includes("network");

    return new ProviderError(
      isOfflineError
        ? "Сервер Ollama недоступен. Запустите Ollama и проверьте доступность http://localhost:11434."
        : "Не удалось подключиться к Ollama. Проверьте локальный сервис и host_permissions.",
      {
        code: "OLLAMA_OFFLINE",
        provider: this.providerName,
        cause: error,
      },
    );
  }
}
