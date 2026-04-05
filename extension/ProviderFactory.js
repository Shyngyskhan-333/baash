import { ProviderError } from "./BaseProvider.js";
import { AzureProvider } from "./AzureProvider.js";
import { OllamaProvider } from "./OllamaProvider.js";
import { OpenAIProvider } from "./OpenAIProvider.js";
import {
  getProviderSettings,
  normalizeProviderName,
} from "./providerSettings.js";

export class ProviderFactory {

  static createProvider(settings) {
    const providerName = normalizeProviderName(settings?.provider);

    switch (providerName) {
      case "azure":
        return new AzureProvider(settings);
      case "ollama":
        return new OllamaProvider(settings);
      case "openai":
        return new OpenAIProvider(settings);
      default:
        throw new ProviderError(` AI-: ${settings?.provider || ""}.`, {
          code: "UNSUPPORTED_PROVIDER",
          provider: providerName || "unknown",
        });
    }
  }

  static async createFromStorage() {
    const settings = await getProviderSettings();
    return this.createProvider(settings);
  }
}