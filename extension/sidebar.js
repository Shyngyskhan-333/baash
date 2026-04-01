const API_URL = "http://localhost:8000/api/v1";
let currentDocId = null;
let chatHistory = [];

// Tab Switching
document.querySelectorAll('.ll-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.ll-tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.ll-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
});

// Initialization from Content Script
window.addEventListener('message', (event) => {
    if (event.data.type === 'INIT_DATA') {
        initAnalyzeData(event.data.data);
    } else if (event.data.type === 'SWITCH_TAB') {
        const btn = document.querySelector(`.ll-tab[data-tab="${event.data.tab}"]`);
        if (btn) btn.click();
    }
});

function initAnalyzeData(data) {
    currentDocId = data.doc_id;
    document.getElementById('analyze-loading').style.display = 'none';
    document.getElementById('analyze-data').style.display = 'block';
    
    // Risk Score
    const riskScore = Math.round(data.risk_score * 100);
    document.getElementById('risk-score').innerText = riskScore;
    const circle = document.getElementById('risk-circle');
    circle.style.borderColor = data.risk_level === 'high' ? '#ef4444' : data.risk_level === 'medium' ? '#f59e0b' : '#22c55e';
    circle.style.color = circle.style.borderColor;

    // AI Summary
    document.getElementById('ai-summary').innerText = data.summary;
    
    // Issues List
    document.getElementById('issues-count').innerText = data.issues.length;
    const list = document.getElementById('issue-list');
    list.innerHTML = '';
    
    data.issues.forEach(issue => {
        const li = document.createElement('li');
        li.className = `ll-issue-item ll-issue-${issue.severity}`;
        
        let typeIcon = issue.type === 'contradiction' ? '⚠️ Коллизия' : issue.type === 'duplicate' ? '📋 Дубликат' : '⏳ Устаревшее';
        
        li.innerHTML = `
            <div class="ll-issue-header">
                <span class="ll-issue-art">${issue.article}</span>
                <span class="ll-issue-type">${typeIcon}</span>
            </div>
            <div class="ll-issue-desc">${issue.description}</div>
            <button class="ll-issue-btn" onclick="scrollToArticle('${issue.article}')">Перейти к статье</button>
        `;
        list.appendChild(li);
    });

    // Related Laws
    const graphList = document.getElementById('graph-list');
    graphList.innerHTML = '';
    if (data.related_laws && data.related_laws.length > 0) {
        data.related_laws.forEach(law => {
            const el = document.createElement('div');
            el.className = 'll-result-item';
            el.innerHTML = `<div class="ll-result-title">${law.title}</div>
                            <div class="ll-result-excerpt">Связь: ${Math.round(law.relevance_score * 100)}%</div>`;
            graphList.appendChild(el);
        });
    } else {
        graphList.innerHTML = '<div class="ll-text-muted">Связанных документов не найдено.</div>';
    }
}

function scrollToArticle(articleNumber) {
    window.parent.postMessage({ type: "SCROLL_TO", article: articleNumber }, "*");
}

// Search Logic
document.getElementById('search-btn').addEventListener('click', async () => {
    const query = document.getElementById('search-input').value;
    const docScope = document.querySelector('input[name="scope"]:checked').value;
    
    if (!query) return;
    
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '<div class="ll-loading">Поиск...</div>';
    
    try {
        const payload = { query: query, top_k: 5 };
        if (docScope === 'document' && currentDocId) {
            payload.filters = { doc_id: currentDocId };
        }
        
        const res = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (data.results.length === 0) {
            resultsContainer.innerHTML = '<div class="ll-text-muted">Ничего не найдено.</div>';
            return;
        }
        
        resultsContainer.innerHTML = '';
        data.results.forEach(r => {
            const item = document.createElement('div');
            item.className = 'll-result-item';
            item.innerHTML = `
                <div class="ll-result-title">${r.title}</div>
                <div class="ll-result-excerpt">${r.excerpt}</div>
            `;
            resultsContainer.appendChild(item);
        });
    } catch (e) {
        resultsContainer.innerHTML = `<div style="color:red;">Ошибка поиска: ${e.message}</div>`;
    }
});

// Chat Logic
document.getElementById('chat-btn').addEventListener('click', sendChatMessage);
document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function sendChatMessage() {
    const inputEl = document.getElementById('chat-input');
    const message = inputEl.value.trim();
    if (!message) return;
    
    const historyContainer = document.getElementById('chat-history');
    
    // Add user message
    historyContainer.innerHTML += `<div class="ll-msg ll-msg-user">${message}</div>`;
    inputEl.value = '';
    
    // Add loading indicator
    const loadingId = 'loading-' + Date.now();
    historyContainer.innerHTML += `<div id="${loadingId}" class="ll-msg ll-msg-system">Думаю...</div>`;
    historyContainer.scrollTop = historyContainer.scrollHeight;
    
    try {
        const payload = {
            message: message,
            doc_id: currentDocId,
            history: chatHistory,
            mode: "general"
        };
        
        const res = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        // Remove loading
        document.getElementById(loadingId).remove();
        
        // Add AI response
        historyContainer.innerHTML += `<div class="ll-msg ll-msg-assistant">${data.answer.replace(/\n/g, '<br>')}</div>`;
        
        if (data.sources && data.sources.length > 0) {
            let sourcesHTML = '<div style="font-size:11px; margin-top:5px; color:#a0aec0;">Источники: ';
            sourcesHTML += data.sources.map(s => s.article).join(', ');
            sourcesHTML += '</div>';
            historyContainer.innerHTML += sourcesHTML;
        }
        
        // Update history
        chatHistory.push({ role: "user", content: message });
        chatHistory.push({ role: "assistant", content: data.answer });
        
        historyContainer.scrollTop = historyContainer.scrollHeight;
    } catch (e) {
        document.getElementById(loadingId).innerHTML = `Ошибка соединения`;
    }
}
