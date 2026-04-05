if (document.contentType === "application/pdf") {
  console.log("LexLens: обнаружен PDF-документ. Меню и сайдбар отключены для стабильности.");
} else {
  const isTopFrame = window.top === window;
  let sidebarOpen = false;
  let selectedText = "";
  let selectionTimeout = null;

  function sendSelectionToTop(payload) {
    if (!payload || !payload.text) {
      return;
    }
    window.top?.postMessage({ type: "LEXLENS_SELECTION", payload }, "*");
  }

  const selectionMenu = isTopFrame ? document.createElement("div") : null;
  if (selectionMenu) {
    selectionMenu.className = "lexlens-selection-menu";
    selectionMenu.style.display = "none";
    document.body.appendChild(selectionMenu);
  }

  const container = isTopFrame ? document.createElement("div") : null;
  if (container) {
    container.id = "lexlens-sidebar-container";
  }

  const iframe = isTopFrame ? document.createElement("iframe") : null;
  if (iframe) {
    iframe.id = "lexlens-sidebar-iframe";
    iframe.src = chrome.runtime.getURL(
      `sidebar.html?v=${encodeURIComponent(chrome.runtime.getManifest().version)}`,
    );
  }

  if (container && iframe) {
    container.appendChild(iframe);
    document.body.appendChild(container);
  }

  const toggleTrigger = isTopFrame ? document.createElement("div") : null;
  if (toggleTrigger) {
    toggleTrigger.id = "lexlens-toggle-trigger";
    toggleTrigger.title = "Открыть LexLens (Alt+L)";
    toggleTrigger.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M15.41,16.59L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.59Z" />
      </svg>
    `;
    document.body.appendChild(toggleTrigger);
  }

  function toggleSidebar(forceOpen = false) {
    if (!container || !toggleTrigger) {
      return;
    }
    sidebarOpen = forceOpen ? true : !sidebarOpen;
    container.classList.toggle("open", sidebarOpen);
    toggleTrigger.classList.toggle("is-open", sidebarOpen);
    if (sidebarOpen) {
      toggleTrigger.classList.remove("has-notification");
    }
  }

  if (toggleTrigger) {
    toggleTrigger.addEventListener("click", () => {
      toggleSidebar();
      if (sidebarOpen && iframe) {
        iframe.contentWindow.postMessage(
          {
            type: "CONTEXT_UPDATE",
            data: getContextPayload("Ручное открытие"),
          },
          "*",
        );
      }
    });
  }

  if (isTopFrame) {
    window.addEventListener("message", (event) => {
      if (event.data?.type === "RESPONSE_READY") {
        if (!sidebarOpen && toggleTrigger) {
          toggleTrigger.classList.add("has-notification");
        }
      } else if (event.data?.type === "TOGGLE_COLLAPSE") {
        toggleSidebar(false);
      } else if (event.data?.type === "LEXLENS_SELECTION") {
        const payload = event.data.payload || {};
        if (payload.text) {
          selectedText = payload.text;
        }
        if (selectionMenu && payload.pageX && payload.pageY) {
          showSelectionMenu(payload.pageX, payload.pageY);
        }
      }
    });
  }

  function hideSelectionMenu() {
    if (selectionMenu) {
      selectionMenu.style.display = "none";
    }
  }

  function showSelectionMenu(pageX, pageY) {
    if (!selectionMenu) return;
    selectionMenu.style.left = `${pageX}px`;
    selectionMenu.style.top = `${Math.max(12, pageY - 56)}px`;
    selectionMenu.style.display = "flex";
  }

  function getSelectionCoords() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return null;
    }
    const rect = selection.getRangeAt(0).getBoundingClientRect();
    if (!rect || rect.width === 0 && rect.height === 0) {
      return null;
    }
    return {
      pageX: rect.right + window.scrollX + 10,
      pageY: rect.top + window.scrollY,
    };
  }

  function extractDocId() {
    const match = window.location.href.match(/\/docs\/([A-Z0-9]+)/);
    return match ? match[1] : null;
  }

  function getDocsSelectionFallback() {
    const selection = window.getSelection();
    if (selection && String(selection).trim()) {
      return String(selection).trim();
    }
    try {
      const iframe = document.querySelector("iframe.docs-texteventtarget-iframe");
      const doc = iframe?.contentDocument || iframe?.contentWindow?.document;
      const node = doc?.querySelector(".kix-appview-editor");
      const raw = node?.innerText || node?.textContent || "";
      const text = String(raw).trim();
      return text.length > 0 ? text.slice(0, 2000) : "";
    } catch {
      return "";
    }
  }

  function getContextPayload(action) {
    const fallbackText = window.location.hostname.includes("docs.google.com")
      ? getDocsSelectionFallback()
      : "";
    return {
      url: window.location.href,
      doc_id: extractDocId(),
      text: selectedText || fallbackText,
      action,
    };
  }

  document.addEventListener("selectionchange", () => {
    clearTimeout(selectionTimeout);
    selectionTimeout = setTimeout(() => {
      const tempText = window.getSelection().toString().trim();
      if (tempText.length > 5 && tempText.length < 2000000) {
        selectedText = tempText;
      } else if (tempText.length >= 2000000) {
        selectedText = `${tempText.substring(0, 1999997)}...`;
      } else {
        selectedText = "";
        hideSelectionMenu();
      }
    }, 150);
  });

  document.addEventListener("mouseup", (event) => {
    if (!isTopFrame) {
      if (selectedText.length > 0) {
        const coords = getSelectionCoords();
        sendSelectionToTop({
          text: selectedText,
          pageX: coords?.pageX ?? event.pageX + 10,
          pageY: coords?.pageY ?? event.pageY,
        });
      }
      return;
    }

    if (
      selectedText.length > 0
      && container
      && !container.contains(event.target)
      && selectionMenu
      && !selectionMenu.contains(event.target)
    ) {
      showSelectionMenu(event.pageX + 10, event.pageY);
    } else if (selectionMenu && !selectionMenu.contains(event.target)) {
      hideSelectionMenu();
    }
  });

  function sendSelectionAction(type, action, pipeline) {
    hideSelectionMenu();
    toggleSidebar(true);

    setTimeout(() => {
      iframe?.contentWindow?.postMessage(
        {
          type,
          pipeline,
          data: getContextPayload(action),
        },
        "*",
      );
    }, 300);
  }

  [
    {
      label: "Открыть в LexLens",
      className: "lexlens-selection-action is-primary",
      type: "SELECTION_CAPTURED",
      action: "Выделение сохранено",
      pipeline: null,
    },
    {
      label: "Поиск связанных НПА",
      className: "lexlens-selection-action",
      type: "SELECTION_ACTION_REQUESTED",
      action: "Поиск связанных НПА",
      pipeline: "find_related_npa",
    },
    {
      label: "Объяснить в LexLens",
      className: "lexlens-selection-action",
      type: "SELECTION_ACTION_REQUESTED",
      action: "Объяснение фрагмента",
      pipeline: "explain_selection",
    },
  ].forEach((item) => {
    if (!selectionMenu) return;
    const actionButton = document.createElement("button");
    actionButton.type = "button";
    actionButton.className = item.className;
    actionButton.textContent = item.label;
    actionButton.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });
    actionButton.addEventListener("click", () => {
      sendSelectionAction(item.type, item.action, item.pipeline);
    });
    selectionMenu.appendChild(actionButton);
  });

  if (isTopFrame) {
    document.addEventListener("keydown", (event) => {
      if (event.altKey && event.code === "KeyL") {
        toggleSidebar();
        if (sidebarOpen) {
        iframe?.contentWindow?.postMessage(
            {
              type: "CONTEXT_UPDATE",
              data: getContextPayload("Ручное открытие"),
            },
            "*",
          );
        }
      }

      if (event.key === "Escape") {
        hideSelectionMenu();
      }
    });

    document.addEventListener("scroll", hideSelectionMenu, true);
  }

  document.addEventListener("copy", (event) => {
    try {
      const copied = event.clipboardData?.getData("text/plain") || "";
      const text = String(copied || "").trim();
      if (text.length > 5) {
        selectedText = text;
        if (!isTopFrame) {
          const coords = getSelectionCoords();
          sendSelectionToTop({
            text: selectedText,
            pageX: coords?.pageX ?? 120,
            pageY: coords?.pageY ?? 120,
          });
        }
      }
    } catch {

    }
  });
}
