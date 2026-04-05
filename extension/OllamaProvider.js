import { BaseProvider, ProviderError } from "./BaseProvider.js";

export class OllamaProvider extends BaseProvider {

  get providerName() {
    return "ollama";
  }

  validateConfig() {
    if (!this.config.ollamaModel) {
      throw new ProviderError(" Ollama    ollamaModel.", {
        code: "OLLAMA_CONFIG_ERROR",
        provider: this.providerName,
      });
    }
  }

  getRequestUrl() {
    const rawUrl = String(this.config.ollamaBaseUrl || "http://localhost:11434").trim();

    if (rawUrl.toLowerCase().includes("/api/chat")) {
      return rawUrl;
    }

    return `${rawUrl.replace(/\/+$/, "")}/api/chat`;
  }

  buildRequestBody(payload) {
    const body = {
      model: this.config.ollamaModel,
      messages: payload.messages,
      stream: false,
      options: {
        ...(payload.options || {}),
      },
    };

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

  parseResponse(data) {
    const answer = this.normalizeMessageContent(data?.message?.content);
    if (!answer) {
      throw new ProviderError("Ollama   .", {
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

  buildHttpError(response, data) {
    if (response.status === 404) {
      return new ProviderError(
        "Endpoint Ollama  . ,      http://localhost:11434.",
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
        " Ollama    (429).   .",
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
        `  Ollama     ${response.status}.`,
      {
        code: "OLLAMA_HTTP_ERROR",
        status: response.status,
        provider: this.providerName,
        details: data,
      },
    );
  }

  buildNetworkError(error) {
    const errorText = String(error?.message || "").toLowerCase();
    const isOfflineError = errorText.includes("fetch") || errorText.includes("network");

    return new ProviderError(
      isOfflineError
        ? " Ollama .  Ollama    http://localhost:11434."
        : "    Ollama.     host_permissions.",
      {
        code: "OLLAMA_OFFLINE",
        provider: this.providerName,
        cause: error,
      },
    );
  }
}