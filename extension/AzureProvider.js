import { BaseProvider, ProviderError } from "./BaseProvider.js";

export class AzureProvider extends BaseProvider {

  get providerName() {
    return "azure";
  }

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
        const hostPart = rawValue.replace(/^https?:\/\//i, "").split("/")[0];
        return hostPart || "";
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

  getRequestUrl() {
    const rawUrl = String(this.config.azureEndpointUrl || "").trim();
    const apiVersion = encodeURIComponent(this.config.azureApiVersion);

    if (rawUrl.toLowerCase().includes("/chat/completions")) {

      if (rawUrl.toLowerCase().includes("api-version=")) {
        return rawUrl;
      }
      return rawUrl.includes("?") ? `${rawUrl}&api-version=${apiVersion}` : `${rawUrl}?api-version=${apiVersion}`;
    }

    const deploymentName = encodeURIComponent(this.config.azureDeploymentName);
    const resourceHost = this.resolveResourceHost();

    if (resourceHost.toLowerCase().includes(".inference.ai.azure.com")) {
      return `https://${resourceHost}/chat/completions?api-version=${apiVersion}`;
    }

    return `https://${resourceHost}/openai/deployments/${deploymentName}/chat/completions?api-version=${apiVersion}`;
  }

  getRequestHeaders() {
    const resourceHost = this.resolveResourceHost();
    const headers = {
      "Content-Type": "application/json",
    };

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

        body.max_completion_tokens = payload.maxTokens;
      } else {
        body.max_tokens = payload.maxTokens;
      }
    }

    return body;
  }

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