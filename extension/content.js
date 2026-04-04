if (document.contentType === "application/pdf") {
  console.log("LexLens: обнаружен PDF-документ. Всплывающее меню и расширение отключены для стабильности.");
} else {
  let sidebarOpen = false;
  let selectedText = "";
  let selectionTimeout = null;

  const selectionMenu = document.createElement("div");
  selectionMenu.className = "lexlens-selection-menu";
  selectionMenu.style.display = "none";
  document.body.appendChild(selectionMenu);

  const container = document.createElement("div");
  container.id = "lexlens-sidebar-container";

  const iframe = document.createElement("iframe");
  iframe.id = "lexlens-sidebar-iframe";
  iframe.src = chrome.runtime.getURL(
    `sidebar.html?v=${encodeURIComponent(chrome.runtime.getManifest().version)}`,
  );

  container.appendChild(iframe);
  document.body.appendChild(container);

  const toggleTrigger = document.createElement("div");
  toggleTrigger.id = "lexlens-toggle-trigger";
  toggleTrigger.title = "Открыть LexLens (Alt+L)";
  toggleTrigger.innerHTML = `
    <svg viewBox="0 0 24 24">
      <path d="M15.41,16.59L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.59Z" />
    </svg>
  `;
  document.body.appendChild(toggleTrigger);

  function toggleSidebar(forceOpen = false) {
    sidebarOpen = forceOpen ? true : !sidebarOpen;
    container.classList.toggle("open", sidebarOpen);
    toggleTrigger.classList.toggle("is-open", sidebarOpen);
    if (sidebarOpen) {
      toggleTrigger.classList.remove("has-notification");
    }
  }

  toggleTrigger.addEventListener("click", () => {
    toggleSidebar();
    if (sidebarOpen) {
      iframe.contentWindow.postMessage(
        {
          type: "CONTEXT_UPDATE",
          data: getContextPayload("Ручное открытие через кнопку"),
        },
        "*",
      );
    }
  });

  window.addEventListener("message", (event) => {
    if (event.data.type === "RESPONSE_READY") {
      if (!sidebarOpen) {
        toggleTrigger.classList.add("has-notification");
      }
    } else if (event.data.type === "TOGGLE_COLLAPSE") {
      toggleSidebar(false);
    }
  });

  function hideSelectionMenu() {
    selectionMenu.style.display = "none";
  }

  function showSelectionMenu(pageX, pageY) {
    selectionMenu.style.left = `${pageX}px`;
    selectionMenu.style.top = `${Math.max(12, pageY - 56)}px`;
    selectionMenu.style.display = "flex";
  }

  function extractDocId() {
    const match = window.location.href.match(/\/docs\/([A-Z0-9]+)/);
    return match ? match[1] : null;
  }

  function getContextPayload(action) {
    return {
      url: window.location.href,
      doc_id: extractDocId(),
      text: selectedText,
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
    if (
      selectedText.length > 0
      && !container.contains(event.target)
      && !selectionMenu.contains(event.target)
    ) {
      showSelectionMenu(event.pageX + 10, event.pageY);
    } else if (!selectionMenu.contains(event.target)) {
      hideSelectionMenu();
    }
  });

  function sendSelectionAction(type, action, pipeline) {
    hideSelectionMenu();
    toggleSidebar(true);

    setTimeout(() => {
      iframe.contentWindow.postMessage(
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
      label: "Найти связанные НПА",
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

  document.addEventListener("keydown", (event) => {
    if (event.altKey && event.code === "KeyL") {
      toggleSidebar();
      if (sidebarOpen) {
        iframe.contentWindow.postMessage(
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


