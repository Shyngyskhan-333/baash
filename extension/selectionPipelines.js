export const SELECTION_PIPELINE_TYPES = Object.freeze({
  EXPLAIN_SELECTION: "explain_selection",
  FIND_RELATED_NPA: "find_related_npa",
});

const PIPELINE_METADATA = Object.freeze({
  [SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION]: {
    buttonLabel: "Объяснить в LexLens",
    sidebarLabel: "Объяснение фрагмента",
    progressLabel: "Анализируем выделенный фрагмент...",
    queuedLabel: "Сначала настройте модель, затем повторите запуск.",
    completionLabel: "Объяснение готово.",
    actionLabel: "Объяснение фрагмента",
  },
  [SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA]: {
    buttonLabel: "Поиск связанных НПА",
    sidebarLabel: "Поиск связанных НПА",
    progressLabel: "Ищем связанные документы...",
    queuedLabel: "Сначала настройте модель, затем повторите поиск.",
    completionLabel: "Связанные НПА найдены.",
    actionLabel: "Поиск связанных НПА",
  },
});

export function getSelectionPipelineMeta(pipeline) {
  return (
    PIPELINE_METADATA[pipeline] || {
      buttonLabel: "Открыть в LexLens",
      sidebarLabel: "Анализ в LexLens",
      progressLabel: "Выполняем запрос...",
      queuedLabel: "Сначала настройте модель.",
      completionLabel: "Готово.",
      actionLabel: "Анализ",
    }
  );
}

function buildContextBlock(context = {}) {
  return [
    `URL: ${context.url || ""}`,
    `Doc ID: ${context.doc_id || ""}`,
    `Действие: ${context.action || "Анализ"}`,
    "Фрагмент:",
    context.text || "",
  ].join("\n");
}

export function buildSelectionPipelineRequest(pipeline, context = {}) {
  const normalizedText = String(context.text || "").trim();
  if (!normalizedText) {
    throw new Error("Сначала выделите фрагмент текста.");
  }

  const contextBlock = buildContextBlock(context);

  if (pipeline === SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION) {
    return {
      messages: [
        {
          role: "system",
          content: "Ты LexLens, юридический ассистент по законодательству Казахстана. Кратко и понятно объясняй значение выделенного фрагмента, указывай практический смысл и не выдумывай ссылки на нормы.",
        },
        {
          role: "user",
          content: `Контекст:\n${contextBlock}\n\nОбъясни фрагмент простым юридическим языком. Дай краткую суть, что это означает на практике и на что обратить внимание.`,
        },
      ],
      temperature: 0.2,
      maxTokens: 4000,
    };
  }

  if (pipeline === SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA) {
    return {
      messages: [
        {
          role: "system",
          content: "Ты LexLens, юридический ассистент по законодательству Казахстана. По выделенному фрагменту найди связанные НПА или типы документов, которые стоит проверить дальше. Не придумывай точные статьи, если не уверен.",
        },
        {
          role: "user",
          content: `Контекст:\n${contextBlock}\n\nНазови 3-5 связанных НПА или направлений поиска. Для каждого кратко объясни, почему он релевантен.`,
        },
      ],
      temperature: 0.2,
      maxTokens: 4000,
    };
  }

  throw new Error(`Неизвестный pipeline: ${pipeline}`);
}