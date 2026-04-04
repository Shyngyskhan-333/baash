import { BaseProvider, ProviderError } from "./BaseProvider.js";

/**
 * Strategy implementation for Azure OpenAI chat completions.
 */
export class AzureProvider extends BaseProvider {
  /**
   * Returns the provider key.
   *
   * @returns {string}
   */
  get providerName() {
    return "azure";
  }

  /**
   * Validates the Azure configuration from storage.
   */
  validateConfig() {
    const missingFields = [
      !this.config.azureApiKey && "azureApiKey",
      !(this.config.azureEndpointUrl || this.config.azureResourceName) &&
        "azureEndpointUrl",
      !this.config.azureDeploymentName && "azureDeploymentName",
      !this.config.azureApiVersion && "azureApiVersion",
    ].filter(Boolean);

    if (missingFields.length > 0) {
      throw new ProviderError(
        `Для Azure OpenAI не заполнены обязательные настройки: ${missingFields.join(", ")}.`,
        {
          code: "AZURE_CONFIG_ERROR",
          provider: this.providerName,
        },
      );
    }
  }

  /**
   * Resolves a saved Azure resource value into a host name.
   *
   * @returns {string}
   */
  resolveResourceHost() {
    const rawValue = String(
      this.config.azureEndpointUrl || this.config.azureResourceName || "",
    )
      .trim()
      .replace(/\/+$/, "");

    if (!rawValue) {
      return "";
    }

    if (/^https?:\/\//i.test(rawValue)) {
      try {
        return new URL(rawValue).host;
      } catch {
        return rawValue.replace(/^https?:\/\//i, "");
      }
    }

    if (rawValue.includes("/")) {
      return rawValue.split("/")[0];
    }

    if (rawValue.includes(".")) {
      return rawValue;
    }

    return `${rawValue}.openai.azure.com`;
  }

  /**
   * Builds the Azure chat completions endpoint.
   *
   * @returns {string}
   */
  getRequestUrl() {
    const rawUrl = String(this.config.azureEndpointUrl || "").trim();
    const apiVersion = encodeURIComponent(this.config.azureApiVersion);

    // If the user provided a full completions path, use it as-is
    if (rawUrl.toLowerCase().includes("/chat/completions")) {
      // Don't append if it already has api-version
      if (rawUrl.toLowerCase().includes("api-version=")) {
        return rawUrl;
      }
      return rawUrl.includes("?") ? `${rawUrl}&api-version=${apiVersion}` : `${rawUrl}?api-version=${apiVersion}`;
    }

    const deploymentName = encodeURIComponent(this.config.azureDeploymentName);
    const resourceHost = this.resolveResourceHost();

    // Support Azure AI Inference host pattern
    if (resourceHost.toLowerCase().includes(".inference.ai.azure.com")) {
      return `https://${resourceHost}/chat/completions?api-version=${apiVersion}`;
    }

    // Default Azure OpenAI deployment pattern
    return `https://${resourceHost}/openai/deployments/${deploymentName}/chat/completions?api-version=${apiVersion}`;
  }

  /**
   * Returns the Azure request headers.
   *
   * @returns {Record<string, string>}
   */
  getRequestHeaders() {
    const resourceHost = this.resolveResourceHost();
    const headers = {
      "Content-Type": "application/json",
    };

    // Azure AI Inference often requires Bearer token, Azure OpenAI uses 'api-key'
    if (
      resourceHost.toLowerCase().includes(".inference.ai.azure.com") ||
      this.config.azureEndpointUrl?.toLowerCase().includes(".inference.ai.azure.com")
    ) {
      headers["Authorization"] = `Bearer ${this.config.azureApiKey}`;
    } else {
      headers["api-key"] = this.config.azureApiKey;
    }

    return headers;
  }

  /**
   * Builds the Azure chat request body.
   *
   * @param {object} payload
   * @returns {object}
   */
  buildRequestBody(payload) {
    const body = {
      messages: payload.messages,
      stream: false,
    };

    if (typeof payload.temperature === "number") {
      body.temperature = payload.temperature;
    }

    if (Number.isInteger(payload.maxTokens)) {
      const deploymentLower = String(this.config.azureDeploymentName || "").toLowerCase();
      const isModernModel = deploymentLower.includes("o1") || deploymentLower.includes("gpt-5");

      if (isModernModel) {
        // o1 models strictly forbid 'max_tokens'
        body.max_completion_tokens = payload.maxTokens;
      } else {
        body.max_tokens = payload.maxTokens;
      }
    }

    return body;
  }

  /**
   * Extracts the assistant message from the Azure response.
   *
   * @param {object|string|null} data
   * @returns {object}
   */
  parseResponse(data) {
    const content = data?.choices?.[0]?.message?.content ?? 
                   data?.choices?.[0]?.text ?? 
                   data?.choices?.[0]?.message?.reasoning_content;
    const finishReason = data?.choices?.[0]?.finish_reason;
    const answer = this.normalizeMessageContent(content);

    if (!answer) {
      let errorMessage = "Azure OpenAI вернул пустой ответ.";
      if (finishReason === "content_filter") {
        errorMessage = "Запрос заблокирован политикой Azure Content Filter.";
      } else if (finishReason === "length") {
        errorMessage = "Ответ был обрезан из-за превышения лимита токенов.";
      } else if (finishReason) {
        errorMessage = `Запрос завершился с кодом: ${finishReason}. Содержимое пустое.`;
      }

      throw new ProviderError(errorMessage, {
        code: "AZURE_EMPTY_RESPONSE",
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
   * Maps Azure-specific HTTP failures to stable UI errors.
   *
   * @param {Response} response
   * @param {object|string|null} data
   * @returns {ProviderError}
   */
  buildHttpError(response, data) {
    if (response.status === 401 || response.status === 403) {
      return new ProviderError(
        "Недействительные учётные данные Azure. Проверьте endpoint URL, API-ключ и доступ к deployment.",
        {
          code: "AZURE_AUTH_ERROR",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    if (response.status === 404) {
      return new ProviderError(
        "Deployment Azure не найден. Проверьте endpoint URL и имя deployment в настройках.",
        {
          code: "AZURE_DEPLOYMENT_NOT_FOUND",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    if (response.status === 429) {
      return new ProviderError(
        "Для Azure OpenAI достигнут лимит запросов (429). Повторите попытку позже.",
        {
          code: "AZURE_RATE_LIMITED",
          status: response.status,
          provider: this.providerName,
          details: data,
        },
      );
    }

    return new ProviderError(
      this.extractErrorMessage(data) ||
        `Запрос к Azure OpenAI завершился ошибкой со статусом ${response.status}.`,
      {
        code: "AZURE_HTTP_ERROR",
        status: response.status,
        provider: this.providerName,
        details: data,
      },
    );
  }

  /**
   * Maps Azure transport failures to a stable network error.
   *
   * @param {Error} error
   * @returns {ProviderError}
   */
  buildNetworkError(error) {
    return new ProviderError(
      "Не удалось подключиться к Azure OpenAI. Проверьте endpoint URL, сеть и host_permissions для *.openai.azure.com.",
      {
        code: "AZURE_NETWORK_ERROR",
        provider: this.providerName,
        cause: error,
      },
    );
  }
}
