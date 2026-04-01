const API_URL = "http://localhost:8000/api/v1";
let currentDocId = null;
let analysisData = null;

// 1. АВТОДЕТЕКТ ДОКУМЕНТА
function extractDocId() {
  const url = window.location.href;
  const match = url.match(/\/docs\/([A-Z0-9]+)/);
  if (match) return match[1];
  
  const urlParams = new URLSearchParams(window.location.search);
  const id = urlParams.get('id');
  if (id) return id;
  
  return null;
}

// 2. RISK BADGE & INJECTION
function injectRiskBadge(riskScore, riskLevel) {
  const titleEl = document.querySelector("h1") || document.querySelector(".inner_main");
  if (!titleEl) return;
  
  const badge = document.createElement("div");
  badge.className = `ll-badge ll-badge-${riskLevel}`;
  badge.innerHTML = `
    <span class="ll-badge-icon">
       ${riskLevel === 'high' ? '🔴' : riskLevel === 'medium' ? '🟡' : '🟢'}
    </span>
    <span class="ll-badge-text">LexLens: ${Math.round(riskScore * 100)}/100</span>
  `;
  
  badge.addEventListener("click", toggleSidebar);
  titleEl.parentElement.insertBefore(badge, titleEl.nextSibling);
}

// 3. SMART HIGHLIGHT
function highlightIssues() {
  if (!analysisData || !analysisData.issues) return;
  
  const paragraphs = document.querySelectorAll("p, h2, h3, h4, h5");
  
  analysisData.issues.forEach(issue => {
    // Find paragraph that starts with the article number
    for (let p of paragraphs) {
      if (p.textContent.startsWith(issue.article)) {
        p.classList.add("ll-highlight", `ll-highlight-${issue.severity}`);
        p.setAttribute("data-ll-tooltip", `${issue.type === 'contradiction' ? 'Коллизия' : issue.type === 'duplicate' ? 'Дубликат' : 'Устаревшее'}: ${issue.description}`);
        
        // Add click to open sidebar to this issue
        p.addEventListener("click", () => {
          openSidebarTab('analyze');
        });
        break;
      }
    }
  });
}

// 4. SIDEBAR INJECTION
function injectSidebar() {
  const sidebar = document.createElement("div");
  sidebar.id = "ll-sidebar";
  sidebar.className = "ll-sidebar-closed";
  
  const iframe = document.createElement("iframe");
  iframe.src = chrome.runtime.getURL("sidebar.html");
  iframe.id = "ll-sidebar-frame";
  
  sidebar.appendChild(iframe);
  document.body.appendChild(sidebar);
  
  // Floating trigger button
  const trigger = document.createElement("div");
  trigger.id = "ll-trigger";
  trigger.innerHTML = "L";
  trigger.title = "LexLens AI";
  trigger.addEventListener("click", toggleSidebar);
  document.body.appendChild(trigger);
}

let isSidebarOpen = false;
function toggleSidebar() {
  const sidebar = document.getElementById("ll-sidebar");
  if (isSidebarOpen) {
    sidebar.classList.remove("ll-sidebar-open");
    sidebar.classList.add("ll-sidebar-closed");
    document.body.style.marginRight = "0";
  } else {
    sidebar.classList.remove("ll-sidebar-closed");
    sidebar.classList.add("ll-sidebar-open");
    document.body.style.marginRight = "380px";
    
    // Send data to iframe
    if (analysisData) {
      const iframe = document.getElementById("ll-sidebar-frame");
      iframe.contentWindow.postMessage({ type: "INIT_DATA", data: analysisData }, "*");
    }
  }
  isSidebarOpen = !isSidebarOpen;
}

function openSidebarTab(tabName) {
    if (!isSidebarOpen) toggleSidebar();
    const iframe = document.getElementById("ll-sidebar-frame");
    iframe.contentWindow.postMessage({ type: "SWITCH_TAB", tab: tabName }, "*");
}

async function analyzeCurrentDoc() {
  try {
    const response = await fetch(`${API_URL}/analyze/${currentDocId}`);
    if (response.ok) {
        analysisData = await response.json();
        injectRiskBadge(analysisData.risk_score, analysisData.risk_level);
        highlightIssues();
        
        // Update iframe if open
        if (isSidebarOpen) {
            const iframe = document.getElementById("ll-sidebar-frame");
            iframe.contentWindow.postMessage({ type: "INIT_DATA", data: analysisData }, "*");
        }
    } else {
        console.error("LexLens: Analysis failed", await response.text());
    }
  } catch (e) {
    console.error("LexLens: API Error", e);
  }
}

// MAIN
currentDocId = extractDocId();
if (currentDocId) {
    console.log("LexLens: Detected Doc ID", currentDocId);
    injectSidebar();
    // Auto request analysis limit wait 2 sec
    setTimeout(analyzeCurrentDoc, 1000);
}

// Listen to messages from Sidebar iframe
window.addEventListener("message", (event) => {
    if (event.data.type === "SCROLL_TO") {
        const paragraphs = document.querySelectorAll("p, h2, h3, h4, h5");
        for (let p of paragraphs) {
            if (p.textContent.startsWith(event.data.article)) {
                p.scrollIntoView({ behavior: 'smooth', block: 'center' });
                p.style.backgroundColor = 'rgba(99, 102, 241, 0.3)';
                setTimeout(() => p.style.backgroundColor = '', 2000);
                break;
            }
        }
    }
});
