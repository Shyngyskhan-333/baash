

export class ProviderError extends Error {

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

export class BaseProvider {

  constructor(config = {}) {
    if (new.target === BaseProvider) {
      throw new TypeError("BaseProvider is abstract and cannot be instantiated directly.");
    }

    this.config = config;
  }

  get providerName() {
    throw new Error("providerName must be implemented by subclasses.");
  }

  validateConfig() {
    throw new Error("validateConfig must be implemented by subclasses.");
  }

  getRequestUrl(_payload) {
    throw new Error("getRequestUrl must be implemented by subclasses.");
  }

  getRequestHeaders(_payload) {
    return {
      "Content-Type": "application/json",
    };
  }

  buildRequestBody(_payload) {
    throw new Error("buildRequestBody must be implemented by subclasses.");
  }

  parseResponse(_data) {
    throw new Error("parseResponse must be implemented by subclasses.");
  }

  buildHttpError(response, data) {
    if (response.status === 429) {
      return new ProviderError("   (429).   .", {
        code: "RATE_LIMITED",
        status: response.status,
        provider: this.providerName,
        details: data,
      });
    }

    const message =
      this.extractErrorMessage(data) ||
      `  ${this.providerName}     ${response.status}.`;

    return new ProviderError(message, {
      code: "HTTP_ERROR",
      status: response.status,
      provider: this.providerName,
      details: data,
    });
  }

  buildNetworkError(error) {
    return new ProviderError(`    ${this.providerName}.`, {
      code: "NETWORK_ERROR",
      provider: this.providerName,
      cause: error,
    });
  }

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
      throw new ProviderError("     .", {
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