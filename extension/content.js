if (document.contentType === 'application/pdf') {
    console.log("LexLens: PDF document detected. Hover and extension disabled for stability.");
} else {
    let sidebarOpen = false;
    let selectedText = '';
    let selectionTimeout = null;

    // Create selection button
    const selectBtn = document.createElement('button');
    selectBtn.className = 'lexlens-selection-btn';
    selectBtn.innerText = '✨ LexLens Analysis';
    selectBtn.style.display = 'none';
    document.body.appendChild(selectBtn);

    // Create sidebar container (shadow dom is possible, but we use an iframe for complete isolation from host site)
    const container = document.createElement('div');
    container.id = 'lexlens-sidebar-container';

    // Disable host styles bleeding by using iframe
    const iframe = document.createElement('iframe');
    iframe.id = 'lexlens-sidebar-iframe';
    iframe.src = chrome.runtime.getURL('sidebar.html');
    
    container.appendChild(iframe);
    document.body.appendChild(container);

    function toggleSidebar(forceOpen = false) {
        sidebarOpen = forceOpen ? true : !sidebarOpen;
        if (sidebarOpen) {
            container.classList.add('open');
        } else {
            container.classList.remove('open');
        }
    }

    // Capture text selection but debounce it so rapid selections don't break things
    document.addEventListener('selectionchange', () => {
        clearTimeout(selectionTimeout);
        selectionTimeout = setTimeout(() => {
            const tempText = window.getSelection().toString().trim();
            if (tempText.length > 5 && tempText.length < 5000) { // arbitrary limit to prevent mega selections breaking prompt
                selectedText = tempText;
            } else if (tempText.length >= 5000) {
                // Trucate long text
                selectedText = tempText.substring(0, 4997) + '...';
            } else {
                selectedText = '';
                selectBtn.style.display = 'none';
            }
        }, 150);
    });

    document.addEventListener('mouseup', (e) => {
        // Truncate logic is handled in selectionchange
        if (selectedText.length > 0 && !container.contains(e.target) && e.target !== selectBtn) {
            // Position button near cursor
            selectBtn.style.top = `${e.pageY - 40}px`;
            selectBtn.style.left = `${e.pageX + 10}px`;
            selectBtn.style.display = 'block';
        } else if (e.target !== selectBtn) {
            selectBtn.style.display = 'none';
        }
    });

    // Handle extraction of doc ID from Adilet website
    function extractDocId() {
        const match = window.location.href.match(/\/docs\/([A-Z0-9]+)/);
        return match ? match[1] : null;
    }

    // Context synchronization payload
    function getContextPayload(action) {
        return {
            url: window.location.href,
            doc_id: extractDocId(),
            text: selectedText,
            action: action
        };
    }

    selectBtn.addEventListener('click', () => {
        selectBtn.style.display = 'none';
        toggleSidebar(true);
        
        // Wait for iframe to be ready before sending
        setTimeout(() => {
            iframe.contentWindow.postMessage({
                type: 'TRIGGER_CHAT',
                data: getContextPayload('Analyze Selection')
            }, '*');
        }, 500);
    });

    // Generic keyboard shortcut listener to just open the sidebar
    document.addEventListener('keydown', (e) => {
        if (e.altKey && e.code === 'KeyL') { // Alt+L toggle
            toggleSidebar();
            if (sidebarOpen) {
                iframe.contentWindow.postMessage({
                    type: 'CONTEXT_UPDATE',
                    data: getContextPayload('General Activation')
                }, '*');
            }
        }
    });
}
