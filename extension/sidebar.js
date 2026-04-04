import {
  Settings,
  loadSettings,
  saveSettings,
  sendChatRequest,
  sendSelectionPipelineRequest,
  testProviderConnection,
} from "./api.js";
import {
  getProviderLabel,
  getProviderReadiness,
} from "./providerSettings.js";
import {
  getSelectionPipelineMeta,
  SELECTION_PIPELINE_TYPES,
} from "./selectionPipelines.js";

const currentContext = {
  url: "",
  doc_id: "",
  text: "",
  action: "",
};

const chatTimeline = [];

const uiState = {
  connectionPhase: "idle",
  connectionMessage: "Завершите настройку, чтобы открыть доступ к анализу.",
  hasUnsavedChanges: false,
  pendingResponse: false,
  pendingPipeline: null,
  suspendFormEvents: false,
};

/**
 * Returns an element by id.
 *
 * @param {string} id
 * @returns {HTMLElement|null}
 */
function byId(id) {
  return document.getElementById(id);
}

/**
 * Escapes arbitrary text for safe HTML output.
 *
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
  const node = document.createElement("div");
  node.textContent = text;
  return node.innerHTML;
}

/**
 * Formats simple markdown markers in escaped content.
 *
 * @param {string} text
 * @returns {string}
 */
function formatInline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/(^|[^\w])_([^_\n]+)_(?!\w)/g, "$1<em>$2</em>");
}

/**
 * Formats provider output into message HTML.
 *
 * @param {string} text
 * @returns {string}
 */
function formatResponse(text) {
  const lines = escapeHtml(text || "").split(/\r?\n/);
  const htmlParts = [];
  let listType = null;

  /**
   * Closes an open list if needed.
   */
  function closeList() {
    if (!listType) {
      return;
    }

    htmlParts.push(`</${listType}>`);
    listType = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    const headingMatch = line.match(/^#{1,6}\s*(.+)$/);
    const dividerMatch = line.match(/^[-*_]{3,}$/);
    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);

    if (headingMatch) {
      closeList();
      htmlParts.push(`<p class="ll-msg-heading">${formatInline(headingMatch[1])}</p>`);
      continue;
    }

    if (dividerMatch) {
      closeList();
      htmlParts.push('<div class="ll-msg-divider" aria-hidden="true"></div>');
      continue;
    }

    if (bulletMatch || orderedMatch) {
      const nextListType = orderedMatch ? "ol" : "ul";
      if (listType && listType !== nextListType) {
        closeList();
      }

      if (!listType) {
        listType = nextListType;
        htmlParts.push(`<${listType}>`);
      }

      htmlParts.push(
        `<li>${formatInline((orderedMatch || bulletMatch)[1])}</li>`,
      );
      continue;
    }

    closeList();

    if (line.length > 0) {
      htmlParts.push(`<p>${formatInline(line)}</p>`);
    }
  }

  closeList();

  return htmlParts.join("") || "<p></p>";
}

/**
 * Shortens a URL for compact UI display with breadcrumb-style formatting.
 *
 * @param {string} url
 * @returns {string}
 */
function summarizeUrl(url) {
  if (!url) {
    return "Контекст страницы не найден.";
  }

  try {
    const parsed = new URL(url);
    const domain = parsed.hostname.toUpperCase();
    const segments = parsed.pathname.split("/").filter((s) => s.length > 0);
    if (segments.length === 0) {
      return domain;
    }
    return `${domain} / ${segments.join(" / ")}`;
  } catch {
    return url;
  }
}

/**
 * Triggers a procedural laser scan animation across the context preview.
 *
 * @returns {Promise<void>}
 */
function triggerScanLine() {
  return new Promise((resolve) => {
    const container = document.querySelector(".ll-context-preview-container");
    if (!container) {
      resolve();
      return;
    }

    container.classList.add("ll-scan-active");
    setTimeout(() => {
      container.classList.remove("ll-scan-active");
      resolve();
    }, 600);
  });
}

/**
 * Creates a short preview for a selection action message.
 *
 * @param {string} text
 * @param {number} [limit=360]
 * @returns {string}
 */
function truncateText(text, limit = 360) {
  const normalizedText = String(text || "").trim();
  if (normalizedText.length <= limit) {
    return normalizedText;
  }

  return `${normalizedText.slice(0, limit - 3)}...`;
}

/**
 * Switches the visible workspace tab with a smooth glide animation.
 *
 * @param {string} tabName
 */
function setActiveTab(tabName) {
  const tabs = document.querySelectorAll(".ll-tab");
  const glide = byId("tabs-glide");
  let activeTab = null;

  tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === tabName;
    tab.classList.toggle("active", isActive);
    if (isActive) {
      activeTab = tab;
    }
  });

  if (activeTab && glide) {
    const tabRect = activeTab.getBoundingClientRect();
    const containerRect = activeTab.parentElement.getBoundingClientRect();

    glide.style.width = `${tabRect.width}px`;
    glide.style.left = `${activeTab.offsetLeft}px`;
  }

  document.querySelectorAll(".ll-content").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });

  // Dispatch custom tabChange event
  window.dispatchEvent(
    new CustomEvent("tabChange", { detail: { tabId: tabName } }),
  );
}

/**
 * Reads the current form values.
 *
 * @returns {object}
 */
function collectSettingsFormData() {
  return {
    provider: byId("ai-provider")?.value || Settings.provider,
    azureEndpointUrl: byId("azure-endpoint-url")?.value?.trim() || "",
    azureDeploymentName: byId("azure-deployment-name")?.value?.trim() || "",
    azureApiVersion: byId("azure-api-version")?.value?.trim() || Settings.azureApiVersion,
    azureApiKey: byId("azure-api-key")?.value?.trim() || "",
    ollamaBaseUrl: byId("ollama-base-url")?.value?.trim() || "",
    ollamaModel: byId("ollama-model")?.value?.trim() || "",
    requestTimeoutMs: Number(byId("request-timeout-ms")?.value || Settings.requestTimeoutMs),
  };
}

/**
 * Returns the readiness summary for saved settings.
 *
 * @returns {object}
 */
function getSavedReadiness() {
  return getProviderReadiness(Settings);
}

/**
 * Returns the readiness summary for the current form state.
 *
 * @returns {object}
 */
function getDraftReadiness() {
  return getProviderReadiness(collectSettingsFormData());
}

/**
 * Applies a visual tone to a chip element.
 *
 * @param {HTMLElement|null} node
 * @param {string} tone
 */
function applyChipTone(node, tone) {
  if (!node) {
    return;
  }

  node.dataset.tone = tone;
}

/**
 * Updates the settings status message.
 *
 * @param {string} message
 * @param {string} [variant="notice"]
 */
function setSettingsStatus(message, variant = "notice") {
  const statusNode = byId("settings-status");
  if (!statusNode) {
    return;
  }

  statusNode.className = `ll-status-msg ${variant}`;
  statusNode.textContent = message;
  statusNode.style.display = message ? "block" : "none";
}

/**
 * Updates the provider selector controls.
 *
 * @param {string} provider
 */
function selectProvider(provider) {
  const providerField = byId("ai-provider");
  if (providerField) {
    providerField.value = provider;
  }

  document.querySelectorAll("[data-provider-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.providerChoice === provider);
  });

  document.querySelectorAll("[data-provider-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.providerPanel !== provider);
  });
}

/**
 * Renders the provider requirement checklist.
 *
 * @param {object} readiness
 */
function renderRequirements(readiness) {
  const container = byId("provider-requirements");
  if (!container) {
    return;
  }

  container.innerHTML = readiness.requirements
    .map(
      (item) => `
        <div class="ll-requirement ${item.present ? "is-complete" : "is-missing"}">
          <span class="ll-requirement-dot"></span>
          <div>
            <strong>${escapeHtml(item.label)}</strong>
            <p>${escapeHtml(item.present ? item.value || item.detail : item.detail)}</p>
          </div>
        </div>
      `,
    )
    .join("");
}

/**
 * Returns a high-level status label for the current setup state.
 *
 * @param {object} readiness
 * @returns {{label: string, tone: string}}
 */
function getConnectionDisplay(readiness) {
  if (uiState.connectionPhase === "testing") {
    return { label: "Проверка", tone: "warning" };
  }

  if (uiState.connectionPhase === "error") {
    return { label: "Ошибка", tone: "danger" };
  }

  if (uiState.connectionPhase === "connected" && !uiState.hasUnsavedChanges) {
    return { label: "Готово", tone: "success" };
  }

  if (readiness.isConfigured) {
    return {
      label: uiState.hasUnsavedChanges ? "Готово к сохранению" : "Настроено",
      tone: "warning",
    };
  }

  return { label: "Нужна настройка", tone: "muted" };
}

/**
 * Renders setup summary and button states.
 */
function renderSetupSurface() {
  const draftReadiness = getDraftReadiness();
  const display = getConnectionDisplay(draftReadiness);

  byId("provider-summary-name").textContent = draftReadiness.providerLabel;
  byId("provider-summary-count").textContent = `${draftReadiness.detectedCount} / ${draftReadiness.totalCount}`;
  byId("provider-summary-state").textContent = display.label;

  selectProvider(draftReadiness.provider);
  renderRequirements(draftReadiness);

  const saveDraftButton = byId("save-settings-draft-btn");
  const saveAndTestButton = byId("save-settings-btn");

  if (saveDraftButton) {
    saveDraftButton.disabled = uiState.connectionPhase === "testing" || !uiState.hasUnsavedChanges;
  }

  if (saveAndTestButton) {
    saveAndTestButton.disabled = uiState.connectionPhase === "testing" || !draftReadiness.isConfigured;
  }
}

/**
 * Renders the selected document context.
 */
function renderContextPanel() {
  byId("doc-id-chip").textContent = currentContext.doc_id
    ? `Документ ${currentContext.doc_id}`
    : "Документ не определён";
  byId("context-preview").textContent = currentContext.text
    ? currentContext.text
    : "Выделите фрагмент на странице, чтобы перенести его сюда как черновик.";
  byId("context-source").textContent = summarizeUrl(currentContext.url);

  const selectionButton = byId("use-selection-btn");
  if (selectionButton) {
    selectionButton.disabled = !currentContext.text || uiState.pendingResponse;
  }

  const explainButton = byId("explain-selection-btn");
  if (explainButton) {
    explainButton.disabled = !currentContext.text || uiState.pendingResponse;
  }

  const relatedButton = byId("find-related-npa-btn");
  if (relatedButton) {
    relatedButton.disabled = !currentContext.text || uiState.pendingResponse;
  }
}

/**
 * Renders the chat history thread.
 */
function renderChatHistory() {
  const historyNode = byId("chat-history");
  if (!historyNode) {
    return;
  }

  if (chatTimeline.length === 0 && !uiState.pendingResponse) {
    historyNode.innerHTML = `
      <div class="ll-empty-thread">
        <span class="ll-eyebrow">Диалог</span>
        <h3>Анализ ещё не отправлялся</h3>
        <p>Выделите текст, проверьте черновик и отправьте запрос после настройки модели.</p>
      </div>
    `;
    return;
  }

  historyNode.innerHTML = chatTimeline
    .map((entry) => {
      if (entry.role === "assistant") {
        return `<article class="ll-msg ll-msg-assistant">${formatResponse(entry.content)}</article>`;
      }

      if (entry.role === "system") {
        return `<article class="ll-msg ll-msg-system">${escapeHtml(entry.content)}</article>`;
      }

      return `<article class="ll-msg ll-msg-user">${escapeHtml(entry.content).replace(/\n/g, "<br>")}</article>`;
    })
    .join("");

  if (uiState.pendingResponse) {
    const pendingLabel = uiState.pendingPipeline
      ? getSelectionPipelineMeta(uiState.pendingPipeline).progressLabel
      : "Готовлю ответ...";
    historyNode.innerHTML += `<article class="ll-msg ll-msg-system"><div class="ll-spinner"></div> ${escapeHtml(pendingLabel)}</article>`;
  }

  historyNode.scrollTop = historyNode.scrollHeight;
}

/**
 * Updates the chat workspace based on saved settings.
 */
function renderChatSurface() {
  const savedReadiness = getSavedReadiness();
  const display = getConnectionDisplay(savedReadiness);
  const composerNode = byId("chat-input");
  const sendButton = byId("chat-btn");
  const gateNode = byId("chat-gate");
  const gateCopyNode = byId("chat-gate-copy");
  const subtitleNode = byId("chat-subtitle");
  const hintNode = byId("chat-hint");
  const headerChip = byId("header-status-chip");
  const providerChip = byId("chat-provider-chip");

  headerChip.textContent = display.label;
  providerChip.textContent = savedReadiness.isConfigured
    ? `${savedReadiness.provider === "azure" ? "Azure" : "Ollama"} готов`
    : "Модель не настроена";

  applyChipTone(headerChip, display.tone);
  applyChipTone(providerChip, savedReadiness.isConfigured ? display.tone : "muted");

  const canChat = savedReadiness.isConfigured && !uiState.pendingResponse;

  composerNode.disabled = !canChat;
  sendButton.disabled = !canChat;

  if (savedReadiness.isConfigured) {
    gateNode.hidden = true;
    gateCopyNode.textContent = "";
    subtitleNode.textContent = currentContext.text
      ? "Выделение сохранено. Проверьте черновик и отправьте запрос, когда будете готовы."
      : `${savedReadiness.providerLabel} готов. Задайте юридический вопрос или добавьте выделенный фрагмент.`;
    hintNode.textContent = uiState.pendingResponse
      ? uiState.pendingPipeline
        ? getSelectionPipelineMeta(uiState.pendingPipeline).progressLabel
        : "Ожидаю ответ от модели..."
      : "Выделенный текст становится черновиком. Отправку контролируете вы.";
    composerNode.placeholder = currentContext.text
      ? "Проверьте подготовленный черновик или уточните его перед отправкой."
      : "Задайте юридический вопрос или вставьте фрагмент для анализа.";
  } else {
    gateNode.hidden = false;
    gateCopyNode.textContent = `Не заполнено: ${savedReadiness.missingRequirements.map((item) => item.label).join(", ")}. Сначала сохраните конфигурацию в разделе настроек.`;
    subtitleNode.textContent = "Выделение можно сохранить уже сейчас, но анализ начнётся только после полной настройки модели.";
    hintNode.textContent = "Чат остаётся заблокированным, пока не сохранены параметры модели и учётные данные.";
    composerNode.placeholder = "Сначала подключите модель, затем проверьте черновик перед отправкой.";
  }
}

/**
 * Re-renders the full UI state.
 */
function renderUi() {
  renderSetupSurface();
  renderContextPanel();
  renderChatSurface();
  renderChatHistory();
}

/**
 * Applies saved settings to the form controls.
 */
function populateSettingsForm() {
  uiState.suspendFormEvents = true;

  byId("ai-provider").value = Settings.provider;
  byId("azure-endpoint-url").value = Settings.azureEndpointUrl;
  byId("azure-deployment-name").value = Settings.azureDeploymentName;
  byId("azure-api-version").value = Settings.azureApiVersion;
  byId("azure-api-key").value = Settings.azureApiKey;
  byId("ollama-base-url").value = Settings.ollamaBaseUrl;
  byId("ollama-model").value = Settings.ollamaModel;
  byId("request-timeout-ms").value = String(Settings.requestTimeoutMs);

  selectProvider(Settings.provider);
  uiState.suspendFormEvents = false;
}

/**
 * Builds the system prompt from the page context.
 *
 * @returns {string}
 */
function buildSystemPrompt() {
  return `Ты LexEntropy, ведущий юридический эксперт по праву Республики Казахстан. 
Твоя задача — консультировать пользователя, опираясь на иерархию НПА РК (Кодексы, Законы, Постановления).

КОНТЕКСТ ТЕКУЩЕЙ СТРАНИЦЫ:
- URL: ${currentContext.url || "неизвестно"}
- ID документа: ${currentContext.doc_id || "неизвестно"}
- Выделенный фрагмент: "${currentContext.text || "нет"}"
- Цель: ${currentContext.action || "общий анализ"}

ИНСТРУКЦИИ:
1. Сначала определи отрасль права, к которой относится вопрос.
2. Отвечай в строгом профессиональном стиле.
3. Если норма требует уточнения в базе "Адилет" или иных источниках, прямо скажи об этом.
4. Ссылайся на конкретные статьи только при полной уверенности. Не гадай.

ОГРАНИЧЕНИЯ (ВАЖНО):
- НЕ используй символы # для заголовков.
- НЕ используй горизонтальные линии ---.
- НЕ используй блоки кода.
- Используй обычные списки 1. 2. 3. для структуры.`;
}

/**
 * Prepares a chat draft from the current selection.
 *
 * @param {boolean} [force=false]
 */
function prepareDraftFromSelection(force = false) {
  const inputNode = byId("chat-input");
  if (!inputNode || !currentContext.text) {
    return;
  }

  if (!force && inputNode.value.trim()) {
    byId("selection-hint").textContent = "Выделение сохранено. Текущий черновик оставлен без изменений.";
    return;
  }

  inputNode.value = `Проанализируй выделенный фрагмент ниже, укажи применимые нормы и объясни его юридическое значение.\n\n${currentContext.text}`;
  byId("selection-hint").textContent = "Черновик подготовлен на основе выделенного текста. Проверьте его перед отправкой.";
}

/**
 * Runs a predefined selection pipeline for the current context.
 *
 * @param {string} pipeline
 */
async function runSelectionPipeline(pipeline) {
  const metadata = getSelectionPipelineMeta(pipeline);
  const savedReadiness = getSavedReadiness();

  if (!currentContext.text) {
    byId("selection-hint").textContent = "Сначала выделите фрагмент.";
    return;
  }

  if (uiState.pendingResponse) {
    byId("selection-hint").textContent = "Дождитесь завершения текущего ответа.";
    return;
  }

  await triggerScanLine();

  uiState.pendingPipeline = pipeline;
  currentContext.action = metadata.actionLabel;

  if (!savedReadiness.isConfigured) {
    setActiveTab("settings");
    setSettingsStatus(metadata.queuedLabel, "notice");
    renderUi();
    return;
  }

  setActiveTab("chat");
  chatTimeline.push({
    role: "user",
    content: `${metadata.sidebarLabel}\n\n${truncateText(currentContext.text)}`,
  });
  uiState.pendingResponse = true;
  byId("selection-hint").textContent = metadata.progressLabel;
  renderUi();

  try {
    const response = await sendSelectionPipelineRequest(
      pipeline,
      currentContext,
      `selection:${pipeline}`,
    );
    chatTimeline.push({ role: "assistant", content: response.answer });
    uiState.connectionPhase = "connected";
    byId("selection-hint").textContent = metadata.completionLabel;
    notifyParentReady();
  } catch (error) {
    chatTimeline.push({
      role: "system",
      content: `Ошибка запроса: ${error.message}`,
    });
    uiState.connectionPhase = "error";
    uiState.connectionMessage = error.message;
    byId("selection-hint").textContent = error.message;
  } finally {
    uiState.pendingResponse = false;
    uiState.pendingPipeline = null;
    renderUi();
  }
}

/**
 * Handles newly selected context from the page.
 *
 * @param {object} data
 */
function handleCapturedSelection(data) {
  Object.assign(currentContext, data || {});
  uiState.pendingPipeline = null;
  renderUi();

  if (getSavedReadiness().isConfigured) {
    setActiveTab("chat");
    prepareDraftFromSelection(false);
    byId("chat-input")?.focus();
    return;
  }

  setActiveTab("settings");
  setSettingsStatus(
    "Выделение сохранено. Сначала выполните конфигурацию в разделе настроек.",
    "notice",
  );
}

/**
 * Handles a quick selection action from the page overlay.
 *
 * @param {string} pipeline
 * @param {object} data
 */
function handleSelectionActionRequest(pipeline, data) {
  Object.assign(currentContext, data || {});
  runSelectionPipeline(pipeline);
}

/**
 * Saves settings and optionally runs a connection test.
 *
 * @param {boolean} shouldTest
 */
async function persistSettings(shouldTest) {
  const actionLabel = shouldTest
    ? "Сохраняю настройки и проверяю подключение..."
    : "Сохраняю настройки...";
  setSettingsStatus(actionLabel, "notice");
  uiState.connectionPhase = shouldTest ? "testing" : "configured";
  renderUi();

  try {
    await saveSettings(collectSettingsFormData());
    await loadSettings();
    uiState.hasUnsavedChanges = false;

    if (shouldTest) {
      await testProviderConnection();
      uiState.connectionPhase = "connected";
      uiState.connectionMessage = `${getProviderLabel(Settings.provider)} успешно ответил.`;
      setSettingsStatus(uiState.connectionMessage, "success");
    } else {
      const readiness = getSavedReadiness();
      uiState.connectionPhase = readiness.isConfigured ? "configured" : "idle";
      uiState.connectionMessage = readiness.isConfigured
        ? `Настройки ${readiness.providerLabel} сохранены. Можно переходить в чат.`
        : "Настройки сохранены. Заполните недостающие поля, чтобы открыть анализ.";
      setSettingsStatus(uiState.connectionMessage, "notice");
    }

    if (getSavedReadiness().isConfigured && uiState.pendingPipeline) {
      const queuedPipeline = uiState.pendingPipeline;
      await runSelectionPipeline(queuedPipeline);
      return;
    }

    if (getSavedReadiness().isConfigured && currentContext.text) {
      prepareDraftFromSelection(false);
      setActiveTab("chat");
    }

    renderUi();
  } catch (error) {
    uiState.connectionPhase = "error";
    uiState.connectionMessage = error.message;
    setSettingsStatus(`Ошибка подключения: ${error.message}`, "error");
    renderUi();
  }
}

/**
 * Sends the chat request through the service worker.
 */
async function sendChatMessage() {
  const savedReadiness = getSavedReadiness();
  const inputNode = byId("chat-input");
  const message = inputNode?.value.trim();

  if (!savedReadiness.isConfigured) {
    setActiveTab("settings");
    setSettingsStatus(
      `Сначала выполните конфигурацию. Не заполнено: ${savedReadiness.missingRequirements.map((item) => item.label).join(", ")}.`,
      "notice",
    );
    return;
  }

  if (!message || uiState.pendingResponse) {
    return;
  }

  chatTimeline.push({ role: "user", content: message });
  inputNode.value = "";
  uiState.pendingResponse = true;
  renderUi();

  const providerHistory = chatTimeline
    .filter((entry) => entry.role === "user" || entry.role === "assistant")
    .map((entry) => ({ role: entry.role, content: entry.content }));

  try {
    const response = await sendChatRequest(
      {
        messages: [
          {
            role: "system",
            content: buildSystemPrompt(),
          },
          ...providerHistory,
        ],
        temperature: 0.2,
      },
      "chat",
    );

    chatTimeline.push({ role: "assistant", content: response.answer });
    uiState.connectionPhase = "connected";
    notifyParentReady();
  } catch (error) {
    chatTimeline.push({ role: "system", content: `Ошибка запроса: ${error.message}` });
    uiState.connectionPhase = "error";
    uiState.connectionMessage = error.message;
  } finally {
    uiState.pendingResponse = false;
    renderUi();
  }
}

/**
 * Marks the form as dirty and refreshes the connect surface.
 */
function handleFormMutation() {
  if (uiState.suspendFormEvents) {
    return;
  }

  uiState.hasUnsavedChanges = true;
  if (uiState.connectionPhase === "connected") {
    uiState.connectionPhase = "configured";
  }

  renderUi();
}

/**
 * Wires DOM and page-context listeners.
 */
function setupListeners() {
  document.querySelectorAll(".ll-tab").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });

  document.querySelectorAll("[data-provider-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      selectProvider(button.dataset.providerChoice);
      handleFormMutation();
    });
  });

  document
    .querySelectorAll("#tab-settings input")
    .forEach((inputNode) => inputNode.addEventListener("input", handleFormMutation));

  byId("save-settings-draft-btn")?.addEventListener("click", () => persistSettings(false));
  byId("save-settings-btn")?.addEventListener("click", () => persistSettings(true));
  byId("chat-connect-cta")?.addEventListener("click", () => setActiveTab("settings"));
  byId("use-selection-btn")?.addEventListener("click", () => {
    prepareDraftFromSelection(true);
    setActiveTab("chat");
  });
  byId("explain-selection-btn")?.addEventListener("click", () => {
    runSelectionPipeline(SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION);
  });
  byId("find-related-npa-btn")?.addEventListener("click", () => {
    runSelectionPipeline(SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA);
  });

  byId("chat-btn")?.addEventListener("click", sendChatMessage);

  byId("chat-input")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  });

  window.addEventListener("message", (event) => {
    if (event.data?.type === "CONTEXT_UPDATE") {
      Object.assign(currentContext, event.data.data || {});
      renderUi();
      return;
    }

    if (event.data?.type === "SELECTION_CAPTURED" || event.data?.type === "TRIGGER_CHAT") {
      handleCapturedSelection(event.data.data || {});
      return;
    }

    if (event.data?.type === "SELECTION_ACTION_REQUESTED") {
      handleSelectionActionRequest(event.data.pipeline, event.data.data || {});
    }
  });
}

/**
 * Notifies the parent window that an AI response is ready.
 */
function notifyParentReady() {
  window.parent.postMessage({ type: "RESPONSE_READY" }, "*");
}

/**
 * Initializes the sidebar.
 */
async function init() {
  await loadSettings();
  populateSettingsForm();

  const savedReadiness = getSavedReadiness();
  uiState.connectionPhase = savedReadiness.isConfigured ? "configured" : "idle";
  uiState.hasUnsavedChanges = false;

  setupListeners();
  renderUi();

  if (!savedReadiness.isConfigured) {
    setActiveTab("settings");
  } else {
    setActiveTab("chat");
  }
}

document.addEventListener("DOMContentLoaded", init);
