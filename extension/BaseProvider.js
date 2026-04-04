/**
 * Normalized provider error with stable metadata for the UI layer.
 */
export class ProviderError extends Error {
  /**
   * Creates a provider error.
   *
   * @param {string} message
   * @param {object} [options={}]
   */
  constructor(message, options = {}) {
    super(message);
    this.name = "ProviderError";
    this.code = options.code || "PROVIDER_ERROR";
    this.status = options.status ?? null;
    this.provider = options.provider || "unknown";
    this.details = options.details ?? null;
    this.cause = options.cause ?? null;
  }
}

/**
 * Abstract strategy interface for AI provider implementations.
 */
export class BaseProvider {
  /**
   * Creates a provider strategy instance.
   *
   * @param {object} config
   */
  constructor(config = {}) {
    if (new.target === BaseProvider) {
      throw new TypeError("BaseProvider is abstract and cannot be instantiated directly.");
    }

    this.config = config;
  }

  /**
   * Returns the stable provider key.
   *
   * @returns {string}
   */
  get providerName() {
    throw new Error("providerName must be implemented by subclasses.");
  }

  /**
   * Validates provider configuration before a request is sent.
   */
  validateConfig() {
    throw new Error("validateConfig must be implemented by subclasses.");
  }

  /**
   * Returns the destination URL for the request.
   *
   * @param {object} _payload
   * @returns {string}
   */
  getRequestUrl(_payload) {
    throw new Error("getRequestUrl must be implemented by subclasses.");
  }

  /**
   * Returns the HTTP headers for the request.
   *
   * @param {object} _payload
   * @returns {Record<string, string>}
   */
  getRequestHeaders(_payload) {
    return {
      "Content-Type": "application/json",
    };
  }

  /**
   * Builds the provider-specific JSON body.
   *
   * @param {object} _payload
   * @returns {object}
   */
  buildRequestBody(_payload) {
    throw new Error("buildRequestBody must be implemented by subclasses.");
  }

  /**
   * Normalizes the raw provider response into UI-facing data.
   *
   * @param {object|string|null} _data
   * @returns {object}
   */
  parseResponse(_data) {
    throw new Error("parseResponse must be implemented by subclasses.");
  }

  /**
   * Maps an HTTP response failure into a ProviderError.
   *
   * @param {Response} response
   * @param {object|string|null} data
   * @returns {ProviderError}
   */
  buildHttpError(response, data) {
    if (response.status === 429) {
      return new ProviderError("Достигнут лимит запросов (429). Повторите попытку позже.", {
        code: "RATE_LIMITED",
        status: response.status,
        provider: this.providerName,
        details: data,
      });
    }

    const message =
      this.extractErrorMessage(data) ||
      `Запрос к ${this.providerName} завершился ошибкой со статусом ${response.status}.`;

    return new ProviderError(message, {
      code: "HTTP_ERROR",
      status: response.status,
      provider: this.providerName,
      details: data,
    });
  }

  /**
   * Maps a transport failure into a ProviderError.
   *
   * @param {Error} error
   * @returns {ProviderError}
   */
  buildNetworkError(error) {
    return new ProviderError(`Не удалось подключиться к ${this.providerName}.`, {
      code: "NETWORK_ERROR",
      provider: this.providerName,
      cause: error,
    });
  }

  /**
   * Executes the provider chat request with normalized error handling.
   *
   * @param {object} payload
   * @param {object} [options={}]
   * @returns {Promise<object>}
   */
  async chat(payload, options = {}) {
    this.validateConfig();

    const messages = Array.isArray(payload?.messages)
      ? payload.messages.filter(
          (message) =>
            message &&
            typeof message.role === "string" &&
            typeof message.content === "string" &&
            message.content.trim().length > 0,
        )
      : [];

    if (!messages.length) {
      throw new ProviderError("Нужно передать хотя бы одно сообщение.", {
        code: "INVALID_REQUEST",
        provider: this.providerName,
      });
    }

    const requestPayload = {
      ...payload,
      messages,
    };

    let response;
    try {
      response = await fetch(this.getRequestUrl(requestPayload), {
        method: "POST",
        headers: this.getRequestHeaders(requestPayload),
        body: JSON.stringify(this.buildRequestBody(requestPayload)),
        signal: options.signal,
      });
    } catch (error) {
      if (error?.name === "AbortError") {
        throw error;
      }

      throw this.buildNetworkError(error);
    }

    const responseData = await this.readResponseBody(response);
    if (!response.ok) {
      throw this.buildHttpError(response, responseData);
    }

    return this.parseResponse(responseData);
  }

  /**
   * Reads and best-effort parses the HTTP response body.
   *
   * @param {Response} response
   * @returns {Promise<object|string|null>}
   */
  async readResponseBody(response) {
    const rawText = await response.text();
    if (!rawText) {
      return null;
    }

    try {
      return JSON.parse(rawText);
    } catch {
      return rawText;
    }
  }

  /**
   * Extracts a readable error message from a parsed response body.
   *
   * @param {object|string|null} data
   * @returns {string}
   */
  extractErrorMessage(data) {
    if (!data) {
      return "";
    }

    if (typeof data === "string") {
      return data;
    }

    if (typeof data.error === "string") {
      return data.error;
    }

    if (typeof data.error?.message === "string") {
      return data.error.message;
    }

    if (typeof data.message === "string") {
      return data.message;
    }

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return "";
  }

  /**
   * Converts provider message payloads into plain text.
   *
   * @param {string|Array<object|string>} content
   * @returns {string}
   */
  normalizeMessageContent(content) {
    if (typeof content === "string") {
      return content.trim();
    }

    if (!Array.isArray(content)) {
      return "";
    }

    return content
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (typeof item?.text === "string") {
          return item.text;
        }

        if (typeof item?.content === "string") {
          return item.content;
        }

        return "";
      })
      .filter(Boolean)
      .join("\n")
      .trim();
  }
}
