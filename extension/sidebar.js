import { Settings, loadSettings, saveSettings, safeFetch } from './api.js';

let currentContext = {
    url: '',
    doc_id: '',
    text: '',
    action: ''
};
let chatHistory = [];

async function init() {
    await loadSettings();
    document.getElementById('api-url').value = Settings.apiUrl;
    document.getElementById('ai-provider').value = Settings.provider;
    
    setupTabs();
    setupListeners();
}

function setupTabs() {
    document.querySelectorAll('.ll-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.ll-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.ll-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
        });
    });
}

function setupListeners() {
    // Context updates from content.js
    window.addEventListener('message', (event) => {
        if (event.data.type === 'CONTEXT_UPDATE') {
            currentContext = { ...currentContext, ...event.data.data };
        } else if (event.data.type === 'TRIGGER_CHAT') {
            currentContext = { ...currentContext, ...event.data.data };
            const msg = `Пожалуйста, проанализируй выделенный фрагмент: "${currentContext.text}"`;
            document.getElementById('chat-input').value = msg;
            
            // Switch to chat tab
            document.querySelector('.ll-tab[data-tab="chat"]').click();
            sendChatMessage();
        }
    });

    // Settings save
    document.getElementById('save-settings-btn').addEventListener('click', async () => {
        const url = document.getElementById('api-url').value.trim();
        const prov = document.getElementById('ai-provider').value;
        const msgDiv = document.getElementById('settings-status');
        
        msgDiv.className = 'll-status-msg';
        msgDiv.innerText = 'Сохранение и проверка...';
        msgDiv.style.display = 'block';

        await saveSettings(url, prov);

        try {
            // Mock test connection. Real app would call setting test endpoint: (/api/v1/settings/ai/test)
            // But we will test by querying the search endpoint with a dummy query
            await safeFetch('test', '/api/v1/search', { query: 'test', top_k: 1 });
            msgDiv.className = 'll-status-msg success';
            msgDiv.innerText = 'Успешно подключено!';
        } catch (e) {
            msgDiv.className = 'll-status-msg error';
            msgDiv.innerText = `Ошибка подключения: ${e.message}`;
        }
    });

    // Chat
    document.getElementById('chat-btn').addEventListener('click', sendChatMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

async function sendChatMessage() {
    const inputEl = document.getElementById('chat-input');
    let message = inputEl.value.trim();
    if (!message) return;
    
    const historyContainer = document.getElementById('chat-history');
    
    // Add user message
    historyContainer.innerHTML += `<div class="ll-msg ll-msg-user">${message}</div>`;
    inputEl.value = '';
    
    // System Prompt injected mandatorily
    const systemPrompt = `You are LexEntropy Legal Assistant embedded in a browser extension.
The user is reading Kazakhstan legislation on ${currentContext.url || 'a webpage'}.
Document ID: ${currentContext.doc_id || 'Unknown'}.
Selected text: "${currentContext.text || 'None'}".
Action: ${currentContext.action || 'General query'}.
Respond in formal legal Russian.
Cite exact articles.
Do not hallucinate document IDs.
Return structured legal analysis.`;

    const loadingId = 'loading-' + Date.now();
    historyContainer.innerHTML += `<div id="${loadingId}" class="ll-msg ll-msg-system">
        <div class="ll-spinner"></div> Анализ...
    </div>`;
    historyContainer.scrollTop = historyContainer.scrollHeight;
    
    try {
        // Prepare chat history mapping for the backend format
        const payload = {
            message: message,
            doc_id: currentContext.doc_id || null,
            history: chatHistory,
            mode: "general",
            system_extra: systemPrompt // if backend supports system merging, or we can inject into history. Let's just push it to 'history' as a system message.
        };
        
        // Ensure system prompt is the first message for ChatGPT style if backend handles it
        // Or we prepend it directly inside history
        const apiHistory = [
            { role: "system", content: systemPrompt },
            ...chatHistory
        ];
        
        const res = await safeFetch('chat', '/api/v1/chat', {
            message: message,
            doc_id: currentContext.doc_id || null,
            history: apiHistory,
            mode: "general"
        });
        
        // Remove loading
        const loader = document.getElementById(loadingId);
        if (loader) loader.remove();
        
        // Add AI response
        const htmlAnswer = formatResponse(res.answer);
        historyContainer.innerHTML += `<div class="ll-msg ll-msg-assistant">${htmlAnswer}</div>`;
        
        if (res.sources && res.sources.length > 0) {
            let sourcesHTML = '<div style="font-size:11px; margin-top:5px; color:var(--dim); font-family:var(--font-mono)">Источники: ';
            sourcesHTML += res.sources.map(s => s.article).join(', ');
            sourcesHTML += '</div>';
            historyContainer.innerHTML += sourcesHTML;
        }
        
        // Update history (only keep user/assistant parts)
        chatHistory.push({ role: "user", content: message });
        chatHistory.push({ role: "assistant", content: res.answer });
        
        historyContainer.scrollTop = historyContainer.scrollHeight;
    } catch (e) {
        const loader = document.getElementById(loadingId);
        if (loader) {
            if (e.name === 'AbortError') {
                loader.innerHTML = `Запрос прерван (таймаут или новый запрос).`;
            } else {
                loader.innerHTML = `Ошибка: ${e.message}`;
            }
            loader.className = 'll-msg ll-msg-system error';
            loader.style.color = 'var(--red)';
            loader.style.borderColor = 'var(--red)';
        }
    }
}

function formatResponse(text) {
    if (!text) return "";
    let html = text.replace(/\n(.*?)(\n|$)/g, function(match, p1) {
        if (p1.trim().startsWith('- ') || p1.trim().startsWith('* ')) {
            return `<li>${p1.substring(2)}</li>`;
        }
        return match;
    });
    
    // Convert <li> sequences into <ul>
    html = html.replace(/(<li>.*?<\/li>)/gs, "<ul>$1</ul>");
    // Normalize multi-ul chunks
    html = html.replace(/<\/ul><ul>/g, "");
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    return html.replace(/\n/g, '<br>');
}

// Start
document.addEventListener('DOMContentLoaded', init);
