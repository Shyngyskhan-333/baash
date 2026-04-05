import { BaseProvider, ProviderError } from "./BaseProvider.js";

export class OpenAIProvider extends BaseProvider {

  get providerName() {
    return "openai";
  }

  validateConfig() {
    const missingFields = [
      !this.config.openaiApiKey && "openaiApiKey",
      !this.config.openaiModel && "openaiModel",
    ].filter(Boolean);

    if (missingFields.length > 0) {
      throw new ProviderError(
        ` OpenAI    : ${missingFields.join(", ")}.`,
        {
          code: "OPENAI_CONFIG_ERROR",
          provider: this.providerName,
        },
      );
    }
  }

  getRequestUrl() {
    const baseUrl = String(this.config.openaiBaseUrl || "https://api.openai.com/v1")
      .trim()
      .replace(/\/+$/, "");

    if (baseUrl.toLowerCase().includes("/chat/completions")) {
      return baseUrl;
    }

    return `${baseUrl}/chat/completions`;
  }

  getRequestHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.config.openaiApiKey}`,
    };
  }

  buildRequestBody(payload) {
    const body = {
      model: this.config.openaiModel,
      messages: payload.messages,
    };

    if (typeof payload.temperature === "number") {
      body.temperature = payload.temperature;
    }

    if (Number.isInteger(payload.maxTokens)) {
      body.max_tokens = payload.maxTokens;
    }

    return body;
  }

  parseResponse(data) {
    const content = data?.choices?.[0]?.message?.content ?? data?.choices?.[0]?.text;
    const answer = this.normalizeMessageContent(content);

    if (!answer) {
      throw new ProviderError("OpenAI   .", {
        code: "OPENAI_EMPTY_RESPONSE",
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
    if (response.status === 401 || response.status === 403) {
      return new ProviderError(
        " API- OpenAI.  openaiApiKey.",
        {
          code: "OPENAI_AUTH_ERROR",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    if (response.status === 429) {
      return new ProviderError(
        " OpenAI    (429).   .",
        {
          code: "OPENAI_RATE_LIMITED",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    return new ProviderError(
      this.extractErrorMessage(data) ||
        `  OpenAI     ${response.status}.`,
      {
        code: "OPENAI_HTTP_ERROR",
        status: response.status,
        provider: this.providerName,
        details: data,
      },
    );
  }

  buildNetworkError(error) {
    return new ProviderError(
      "    OpenAI.    host_permissions  api.openai.com.",
      {
        code: "OPENAI_NETWORK_ERROR",
        provider: this.providerName,
        cause: error,
      },
    );
  }
}