import {
  Settings,
  loadSettings,
  saveSettings,
  sendChatRequest,
  sendSelectionPipelineRequest,
  testProviderConnection,
} from "./api.js";
import { getProviderLabel, getProviderReadiness } from "./providerSettings.js";
import { getSelectionPipelineMeta, SELECTION_PIPELINE_TYPES } from "./selectionPipelines.js";

const currentContext = {
  url: "",
  doc_id: "",
  text: "",
  action: "",
};

const chatTimeline = [];
let pendingResponse = false;
let hasUnsavedChanges = false;

function byId(id) {
  return document.getElementById(id);
}

function setActiveTab(tabName) {
  document.querySelectorAll(".ll-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  const glide = byId("tabs-glide");
  const activeTab = document.querySelector(`.ll-tab[data-tab="${tabName}"]`);
  if (glide && activeTab) {
    glide.style.width = `${activeTab.offsetWidth}px`;
    glide.style.left = `${activeTab.offsetLeft}px`;
  }

  document.querySelectorAll(".ll-content").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });
}

function summarizeUrl(url) {
  if (!url) return "Контекст страницы не найден.";

  try {
    const parsed = new URL(url);
    const parts = parsed.pathname.split("/").filter(Boolean);
    return parts.length ? `${parsed.hostname.toUpperCase()} / ${parts.join(" / ")}` : parsed.hostname.toUpperCase();
  } catch {
    return url;
  }
}

function truncateText(text, limit = 500) {
  const value = String(text || "").trim();
  if (!value) return "Выделите фрагмент на странице, чтобы перенести его сюда как черновик.";
  return value.length > limit ? `${value.slice(0, limit - 3)}...` : value;
}

function escapeHtml(text) {
  const node = document.createElement("div");
  node.textContent = String(text || "");
  return node.innerHTML;
}


function userFacingErrorMessage(error) {
  const msg = String(error?.message ?? error ?? "").trim();
  if (
    /context invalidated|extension context|message port closed|receiving end does not exist/i.test(msg)
  ) {
    return "Обновите страницу (F5) и снова откройте LexLens — расширение было перезагружено.";
  }
  return msg || "Неизвестная ошибка.";
}

function escapeAttr(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;");
}

function formatMessage(text) {
  return escapeHtml(text).replace(/\n/g, "<br>");
}

function extractReasoningBlocks(source) {
  const blocks = [];
  let text = String(source || "");
  const patterns = [
    /<think[^>]*>([\s\S]*?)<\/think>/gi,
    /<reasoning[^>]*>([\s\S]*?)<\/reasoning>/gi,
    /<redacted_thinking>([\s\S]*?)<\/redacted_reasoning>/gi,
    /<redacted_thinking>([\s\S]*?)<\/redacted_thinking>/gi,
  ];
  for (const re of patterns) {
    text = text.replace(re, (_, inner) => {
      blocks.push(String(inner !== undefined ? inner : _).trim());
      return "\n";
    });
  }
  return { text: text.replace(/\n{3,}/g, "\n\n").trim(), blocks };
}

function formatInlineWithBoldAndUrls(text) {
  const raw = String(text || "");
  const parts = raw.split(/(\*\*[^*]+\*\*)/g);
  const escaped = parts
    .map((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) {
        return `<strong>${escapeHtml(part.slice(2, -2))}</strong>`;
      }
      return escapeHtml(part);
    })
    .join("");
  return escaped.replace(/https?:\/\/[^\s<]+/g, (url) => {
    const href = escapeAttr(url.replace(/[),.;]+$/, ""));
    return `<a class="ll-source-pill" href="${href}" target="_blank" rel="noopener noreferrer">Источник</a>`;
  }).replace(/\n/g, "<br>");
}

function formatReasoningDetails(blocks) {
  if (!blocks.length) return "";
  const inner = blocks
    .map(
      (body, i) =>
        `<div class="ll-think-chunk">${blocks.length > 1 ? `<span class="ll-think-chunk-label">Часть ${i + 1}</span>` : ""}${formatMessage(body)}</div>`,
    )
    .join("");
  return `<details class="ll-msg-think">
  <summary class="ll-think-summary">
    <span class="ll-think-title">Ход рассуждения модели</span>
    <span class="ll-think-toggle" aria-hidden="true"></span>
  </summary>
  <div class="ll-think-body ll-think-prose">${inner}</div>
</details>`;
}

function formatAssistantHtml(raw) {
  const { text, blocks } = extractReasoningBlocks(raw);
  const mainHtml = text ? `<div class="ll-msg-prose">${formatInlineWithBoldAndUrls(text)}</div>` : "";
  const thinkHtml = formatReasoningDetails(blocks);
  return `${mainHtml}${thinkHtml}`;
}

function formatRelatedNpaBlock(intro, items) {
  const introHtml = intro
    ? `<p class="ll-npa-intro">${escapeHtml(intro)}</p>`
    : "";
  const cards = items
    .map((it) => {
      const scoreVal = it.score;
      const scoreLabel =
        typeof scoreVal === "number" && Number.isFinite(scoreVal)
          ? scoreVal.toFixed(3)
          : escapeHtml(String(scoreVal ?? ""));
      const link = it.url
        ? `<a class="ll-npa-link-btn" href="${escapeAttr(it.url)}" target="_blank" rel="noopener noreferrer">Открыть на Adilet</a>`
        : "";
      return `<article class="ll-npa-card">
        <div class="ll-npa-card-main">
          <span class="ll-npa-index" aria-hidden="true">${it.index}</span>
          <div class="ll-npa-body">
            <h4 class="ll-npa-title">${escapeHtml(it.title)}</h4>
            <div class="ll-npa-meta">
              <code class="ll-npa-id">${escapeHtml(it.docId || "—")}</code>
              <span class="ll-npa-score">cosine ${scoreLabel}</span>
            </div>
          </div>
        </div>
        ${link}
      </article>`;
    })
    .join("");
  return `<div class="ll-npa-block">${introHtml}<div class="ll-npa-list">${cards}</div></div>`;
}

function renderMessageBody(entry) {
  if (entry.role === "user" || entry.role === "system") {
    return formatMessage(entry.content);
  }
  if (entry.relatedItems?.length) {
    return formatRelatedNpaBlock(entry.content, entry.relatedItems);
  }
  return formatAssistantHtml(entry.content);
}

function entryPlainTextForApi(entry) {
  if (entry.role !== "assistant") return entry.content;
  if (entry.relatedItems?.length) {
    const lines = entry.relatedItems.map(
      (it) =>
        `${it.index}. ${it.title} (${it.docId}) cosine ${typeof it.score === "number" ? it.score.toFixed(3) : it.score}`,
    );
    return [entry.content, ...lines].filter(Boolean).join("\n");
  }
  return entry.content;
}

function getConversationEntries() {
  return chatTimeline.filter((entry) => entry.role === "user" || entry.role === "assistant");
}

function getDraftSettings() {
  return {
    provider: byId("ai-provider")?.value || Settings.provider,
    azureEndpointUrl: byId("azure-endpoint-url")?.value?.trim() || "",
    azureDeploymentName: byId("azure-deployment-name")?.value?.trim() || "",
    azureApiVersion: byId("azure-api-version")?.value?.trim() || Settings.azureApiVersion,
    azureApiKey: byId("azure-api-key")?.value?.trim() || "",
    openaiBaseUrl: byId("openai-base-url")?.value?.trim() || "",
    openaiModel: byId("openai-model")?.value?.trim() || "",
    openaiApiKey: byId("openai-api-key")?.value?.trim() || "",
    ollamaBaseUrl: byId("ollama-base-url")?.value?.trim() || "",
    ollamaModel: byId("ollama-model")?.value?.trim() || "",
    requestTimeoutMs: Number(byId("request-timeout-ms")?.value || Settings.requestTimeoutMs),
  };
}

function applyChipTone(node, tone) {
  if (node) {
    node.dataset.tone = tone;
  }
}

function setSettingsStatus(message, variant = "notice") {
  const node = byId("settings-status");
  if (!node) return;
  node.className = `ll-status-msg ${variant}`;
  node.textContent = message;
  node.style.display = message ? "block" : "none";
}

function selectProvider(provider) {
  const field = byId("ai-provider");
  if (field) {
    field.value = provider;
  }

  document.querySelectorAll("[data-provider-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.providerChoice === provider);
  });

  document.querySelectorAll("[data-provider-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.providerPanel !== provider);
  });
}

function renderRequirements(readiness) {
  const container = byId("provider-requirements");
  if (!container) return;

  container.innerHTML = readiness.requirements.map((item) => `
    <div class="ll-requirement ${item.present ? "is-complete" : "is-missing"}">
      <span class="ll-requirement-dot"></span>
      <div>
        <strong>${item.label}</strong>
        <p>${item.detail}</p>
      </div>
    </div>
  `).join("");
}

function renderHeader(readiness) {
  const statusChip = byId("header-status-chip");
  const providerChip = byId("chat-provider-chip");
  const docChip = byId("doc-id-chip");
  const summaryName = byId("provider-summary-name");
  const summaryCount = byId("provider-summary-count");
  const summaryState = byId("provider-summary-state");
  const gate = byId("chat-gate");
  const gateCopy = byId("chat-gate-copy");

  const tone = readiness.isConfigured ? (pendingResponse ? "warning" : "success") : "muted";
  const text = readiness.isConfigured ? (pendingResponse ? "Идет анализ" : "Контекст готов") : "Нужна настройка";

  if (statusChip) {
    statusChip.textContent = text;
    applyChipTone(statusChip, tone);
  }

  if (providerChip) {
    providerChip.textContent = readiness.isConfigured ? readiness.providerLabel : "Модель не выбрана";
  }

  if (docChip) {
    docChip.textContent = currentContext.doc_id ? `Документ: ${currentContext.doc_id}` : "Документ не определен";
  }

  if (summaryName) summaryName.textContent = getProviderLabel(readiness.provider);
  if (summaryCount) summaryCount.textContent = `${readiness.detectedCount} / ${readiness.totalCount}`;
  if (summaryState) {
    summaryState.textContent = hasUnsavedChanges ? "Есть несохраненные изменения" : readiness.isConfigured ? "Готово" : "Нужна настройка";
  }

  if (gate) gate.hidden = readiness.isConfigured;
  if (gateCopy) {
    gateCopy.textContent = readiness.isConfigured
      ? "Модель подключена."
      : "Сначала укажите провайдера, адрес API и модель в разделе настроек.";
  }
}

function renderContext() {
  const preview = byId("context-preview");
  const source = byId("context-source");
  const hint = byId("selection-hint");

  if (preview) preview.textContent = truncateText(currentContext.text);
  if (source) source.textContent = summarizeUrl(currentContext.url);
  if (hint && !pendingResponse) {
    hint.textContent = currentContext.text
      ? "Контекст обновлен. Запросы не отправляются автоматически."
      : "Запросы не отправляются автоматически.";
  }
}

function renderExplainability() {
  const chip = byId("analysis-stage-chip");
  const summary = byId("analysis-summary");
  const stepper = byId("analysis-stepper");

  if (chip) {
    chip.textContent = pendingResponse ? "Запрос к модели" : currentContext.text ? "Контекст готов" : "Ожидание";
    applyChipTone(chip, pendingResponse ? "warning" : currentContext.text ? "success" : "muted");
  }

  if (summary) {
    summary.textContent = pendingResponse
      ? "Формируем запрос и ждем ответ модели."
      : currentContext.text
        ? "Выделение сохранено. Можно подготовить черновик или сразу запустить анализ."
        : "Ожидаем контекст или запрос.";
  }

  if (stepper) {
    const readiness = getProviderReadiness(getDraftSettings());
    const steps = [
      { title: "Контекст", description: currentContext.text ? `${currentContext.text.length} символов` : "Нет выделения", state: currentContext.text ? "done" : "pending" },
      { title: "Провайдер", description: readiness.providerLabel, state: readiness.isConfigured ? "done" : "pending" },
      { title: "Запрос", description: pendingResponse ? "Выполняется" : "Ожидает запуска", state: pendingResponse ? "active" : "pending" },
    ];

    stepper.innerHTML = steps.map((step, index) => `
      <div class="ll-analysis-step" data-state="${step.state}">
        <div class="ll-analysis-step-index">${index + 1}</div>
        <div>
          <strong>${step.title}</strong>
          <p>${step.description}</p>
        </div>
      </div>
    `).join("");
  }
}

function renderChatHistory() {
  const node = byId("chat-history");
  if (!node) return;

  if (chatTimeline.length === 0) {
    node.innerHTML = `
      <section class="ll-empty-thread">
        <span class="ll-eyebrow">LexLens</span>
        <h3>Чем могу помочь?</h3>
        <p class="ll-help-text">Подготовьте черновик из выделения или задайте вопрос по контексту документа.</p>
      </section>
    `;
    return;
  }

  node.innerHTML = chatTimeline.map((entry) => {
    const roleClass = entry.role === "user" ? "ll-msg-user" : entry.role === "system" ? "ll-msg-system" : "ll-msg-assistant";
    const rich = entry.role === "assistant" && entry.relatedItems?.length ? " ll-msg-rich" : "";
    return `<article class="ll-msg ${roleClass}${rich}">${renderMessageBody(entry)}</article>`;
  }).join("");
  node.scrollTop = node.scrollHeight;
}

function renderUi() {
  const readiness = getProviderReadiness(getDraftSettings());
  renderHeader(readiness);
  renderRequirements(readiness);
  renderContext();
  renderExplainability();
  renderChatHistory();
}

function populateSettingsForm() {
  byId("ai-provider").value = Settings.provider;
  byId("azure-endpoint-url").value = Settings.azureEndpointUrl;
  byId("azure-deployment-name").value = Settings.azureDeploymentName;
  byId("azure-api-version").value = Settings.azureApiVersion;
  byId("azure-api-key").value = Settings.azureApiKey;
  byId("openai-base-url").value = Settings.openaiBaseUrl;
  byId("openai-model").value = Settings.openaiModel;
  byId("openai-api-key").value = Settings.openaiApiKey;
  byId("ollama-base-url").value = Settings.ollamaBaseUrl;
  byId("ollama-model").value = Settings.ollamaModel;
  byId("request-timeout-ms").value = String(Settings.requestTimeoutMs);
  selectProvider(Settings.provider);
}

function addChatEntry(entry) {
  chatTimeline.push(entry);
  if (chatTimeline.length > 200) {
    chatTimeline.splice(0, chatTimeline.length - 200);
  }
}

function clearChatHistory() {
  chatTimeline.splice(0, chatTimeline.length);
  renderUi();
}

function prepareDraftFromSelection(force = false) {
  const input = byId("chat-input");
  const hint = byId("selection-hint");
  if (!input || !currentContext.text) {
    if (hint) hint.textContent = "Сначала выделите фрагмент.";
    return;
  }

  if (!force && input.value.trim()) {
    if (hint) hint.textContent = "Выделение сохранено. Текущий черновик оставлен без изменений.";
    return;
  }

  input.value = `Проанализируй выделенный фрагмент ниже, укажи применимые нормы и объясни его юридическое значение.\n\n${currentContext.text}`;
  if (hint) hint.textContent = "Черновик подготовлен на основе выделенного текста.";
  renderUi();
}

function buildSystemPrompt() {
  return "Ты LexLens, юридический ассистент по законодательству Казахстана. Отвечай кратко, ясно и профессионально. Не выдумывай статьи и нормы, если не уверен.";
}

async function runSelectionPipeline(pipeline) {
  const readiness = getProviderReadiness(Settings);
  const meta = getSelectionPipelineMeta(pipeline);
  const hint = byId("selection-hint");

  if (!currentContext.text) {
    if (hint) hint.textContent = "Сначала выделите фрагмент.";
    return;
  }

  if (!readiness.isConfigured) {
    setActiveTab("settings");
    setSettingsStatus(meta.queuedLabel, "notice");
    return;
  }

  pendingResponse = true;
  addChatEntry({ role: "user", content: `${meta.sidebarLabel}\n\n${truncateText(currentContext.text, 800)}` });
  if (hint) hint.textContent = meta.progressLabel;
  renderUi();

  try {
    const response = await sendSelectionPipelineRequest(pipeline, currentContext, `selection:${pipeline}`);
    addChatEntry({
      role: "assistant",
      content: response.answer,
      ...(response.relatedItems?.length ? { relatedItems: response.relatedItems } : {}),
    });
    if (hint) hint.textContent = meta.completionLabel;
    window.parent.postMessage({ type: "RESPONSE_READY" }, "*");
  } catch (error) {
    addChatEntry({ role: "system", content: userFacingErrorMessage(error) });
    if (hint) hint.textContent = userFacingErrorMessage(error);
  } finally {
    pendingResponse = false;
    renderUi();
  }
}

async function saveCurrentSettings(withTest) {
  setSettingsStatus(withTest ? "Сохраняем настройки и проверяем подключение..." : "Сохраняем настройки...", "notice");

  try {
    await saveSettings(getDraftSettings());
    hasUnsavedChanges = false;
    populateSettingsForm();

    if (withTest) {
      await testProviderConnection();
      setSettingsStatus(`${getProviderLabel(Settings.provider)} отвечает корректно.`, "success");
    } else {
      setSettingsStatus("Настройки сохранены.", "notice");
    }

    renderUi();
  } catch (error) {
    setSettingsStatus(userFacingErrorMessage(error), "error");
  }
}

async function sendChatMessage() {
  const readiness = getProviderReadiness(Settings);
  const input = byId("chat-input");
  const message = input?.value.trim();

  if (!readiness.isConfigured) {
    setActiveTab("settings");
    setSettingsStatus("Сначала заполните настройки провайдера.", "notice");
    return;
  }

  if (!message || pendingResponse) return;

  pendingResponse = true;
  addChatEntry({ role: "user", content: message });
  input.value = "";
  renderUi();

  try {
    const response = await sendChatRequest(
      {
        messages: [
          { role: "system", content: buildSystemPrompt() },
          ...getConversationEntries().map((entry) => ({
            role: entry.role,
            content: entryPlainTextForApi(entry),
          })),
        ],
        temperature: 0.2,
        maxTokens: 4000,
      },
      "chat",
    );

    addChatEntry({ role: "assistant", content: response.answer });
    window.parent.postMessage({ type: "RESPONSE_READY" }, "*");
  } catch (error) {
    addChatEntry({ role: "system", content: userFacingErrorMessage(error) });
  } finally {
    pendingResponse = false;
    renderUi();
  }
}

function handleContext(data = {}) {
  Object.assign(currentContext, data);
  renderUi();
}

function setupListeners() {
  document.querySelectorAll(".ll-tab").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });

  document.querySelectorAll("[data-provider-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      selectProvider(button.dataset.providerChoice);
      hasUnsavedChanges = true;
      renderUi();
    });
  });

  document.querySelectorAll("#tab-settings input").forEach((input) => {
    input.addEventListener("input", () => {
      hasUnsavedChanges = true;
      renderUi();
    });
  });

  byId("save-settings-draft-btn")?.addEventListener("click", () => saveCurrentSettings(false));
  byId("save-settings-btn")?.addEventListener("click", () => saveCurrentSettings(true));
  byId("use-selection-btn")?.addEventListener("click", () => {
    prepareDraftFromSelection(true);
    setActiveTab("chat");
  });
  byId("explain-selection-btn")?.addEventListener("click", () => runSelectionPipeline(SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION));
  byId("find-related-npa-btn")?.addEventListener("click", () => runSelectionPipeline(SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA));
  byId("chat-btn")?.addEventListener("click", sendChatMessage);
  byId("clear-history-btn")?.addEventListener("click", clearChatHistory);
  byId("close-sidebar-btn")?.addEventListener("click", () => {
    window.parent.postMessage({ type: "TOGGLE_COLLAPSE" }, "*");
  });

  byId("chat-input")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  });

  window.addEventListener("message", (event) => {
    if (event.data?.type === "CONTEXT_UPDATE") {
      handleContext(event.data.data || {});
      return;
    }

    if (event.data?.type === "SELECTION_CAPTURED" || event.data?.type === "TRIGGER_CHAT") {
      handleContext(event.data.data || {});
      prepareDraftFromSelection(false);
      setActiveTab("chat");
      return;
    }

    if (event.data?.type === "SELECTION_ACTION_REQUESTED") {
      handleContext(event.data.data || {});
      runSelectionPipeline(event.data.pipeline);
    }
  });
}

async function init() {
  await loadSettings();
  populateSettingsForm();
  setupListeners();
  renderUi();
  setActiveTab(getProviderReadiness(Settings).isConfigured ? "chat" : "settings");
}

document.addEventListener("DOMContentLoaded", init);