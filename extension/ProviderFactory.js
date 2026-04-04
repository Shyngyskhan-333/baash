import { ProviderError } from "./BaseProvider.js";
import { AzureProvider } from "./AzureProvider.js";
import { OllamaProvider } from "./OllamaProvider.js";
import {
  getProviderSettings,
  normalizeProviderName,
} from "./providerSettings.js";

/**
 * Factory for instantiating provider strategies from extension settings.
 */
export class ProviderFactory {
  /**
   * Creates the correct provider instance for a settings object.
   *
   * @param {object} settings
   * @returns {AzureProvider|OllamaProvider}
   */
  static createProvider(settings) {
    const providerName = normalizeProviderName(settings?.provider);

    switch (providerName) {
      case "azure":
        return new AzureProvider(settings);
      case "ollama":
        return new OllamaProvider(settings);
      default:
        throw new ProviderError(`Неподдерживаемый AI-провайдер: ${settings?.provider || "неизвестно"}.`, {
          code: "UNSUPPORTED_PROVIDER",
          provider: providerName || "unknown",
        });
    }
  }

  /**
   * Loads settings from storage and returns the matching provider instance.
   *
   * @returns {Promise<AzureProvider|OllamaProvider>}
   */
  static async createFromStorage() {
    const settings = await getProviderSettings();
    return this.createProvider(settings);
  }
}
