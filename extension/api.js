export const Settings = {
    apiUrl: 'http://localhost:8000',
    provider: 'Ollama',
};

export async function loadSettings() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['apiUrl', 'provider'], (res) => {
            if (res.apiUrl) Settings.apiUrl = res.apiUrl;
            if (res.provider) Settings.provider = res.provider;
            resolve(Settings);
        });
    });
}

export async function saveSettings(apiUrl, provider) {
    Settings.apiUrl = apiUrl;
    Settings.provider = provider;
    return new Promise((resolve) => {
        chrome.storage.local.set({ apiUrl, provider }, resolve);
    });
}

// Global AbortControllers for specific channels
const controllers = {};

/**
 * 
 * @param {string} channel 'search', 'chat', 'diff'
 * @param {string} endpoint e.g., '/api/v1/search'
 * @param {object} payload 
 * @param {object} options 
 */
export async function safeFetch(channel, endpoint, payload, options = {}) {
    // Cancel previous request on the same channel
    if (controllers[channel]) {
        controllers[channel].abort("Cancelled by new request");
    }

    const controller = new AbortController();
    controllers[channel] = controller;
    
    // 30s timeout
    const timeoutId = setTimeout(() => {
        if (controllers[channel] === controller) {
            controller.abort(new Error("Request Timeout"));
        }
    }, 30000);

    try {
        const fullUrl = `${Settings.apiUrl}${endpoint}`;
        
        const response = await fetch(fullUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload),
            signal: controller.signal,
            ...options
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw error; // Let caller know it was cancelled or timed out
        }
        
        console.error(`[API Error (${channel})]`, error);
        throw new Error("Не удалось подключиться к серверу. Убедитесь, что сервер запущен.");
    } finally {
        if (controllers[channel] === controller) {
            delete controllers[channel];
        }
    }
}
