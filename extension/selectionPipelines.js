export const SELECTION_PIPELINE_TYPES = Object.freeze({
  EXPLAIN_SELECTION: "explain_selection",
  FIND_RELATED_NPA: "find_related_npa",
});

const PIPELINE_METADATA = Object.freeze({
  [SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION]: {
    buttonLabel: "Объяснить в LexLens",
    sidebarLabel: "Объяснение фрагмента",
    progressLabel: "Готовлю объяснение фрагмента...",
    queuedLabel: "Объяснение поставлено в очередь. Сначала сохраните настройки модели.",
    completionLabel: "Объяснение готово.",
    actionLabel: "Объяснение выделенного фрагмента",
  },
  [SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA]: {
    buttonLabel: "Найти связанные НПА",
    sidebarLabel: "Поиск связанных НПА",
    progressLabel: "Ищу связанные НПА...",
    queuedLabel: "Поиск связанных НПА поставлен в очередь. Сначала сохраните настройки модели.",
    completionLabel: "Связанные НПА найдены.",
    actionLabel: "Поиск связанных НПА",
  },
});

/**
 * Returns metadata for a selection pipeline.
 *
 * @param {string} pipeline
 * @returns {object}
 */
export function getSelectionPipelineMeta(pipeline) {
  return (
    PIPELINE_METADATA[pipeline] || {
      buttonLabel: "Действие LexLens",
      sidebarLabel: "Действие LexLens",
      progressLabel: "Выполняю действие...",
      queuedLabel: "Действие поставлено в очередь.",
      completionLabel: "Действие завершено.",
      actionLabel: "Действие по выделению",
    }
  );
}

/**
 * Builds a shared context block for selection pipelines.
 *
 * @param {object} context
 * @returns {string}
 */
function buildContextBlock(context = {}) {
  return [
    `URL: ${context.url || "Неизвестно"}`,
    `ID документа: ${context.doc_id || "Неизвестно"}`,
    `Действие: ${context.action || "Работа с выделением"}`,
    "Выделенный текст:",
    context.text || "Нет данных",
  ].join("\n");
}

/**
 * Builds a provider payload for a named selection pipeline.
 *
 * @param {string} pipeline
 * @param {object} context
 * @returns {object}
 */
export function buildSelectionPipelineRequest(pipeline, context = {}) {
  const normalizedText = String(context.text || "").trim();
  if (!normalizedText) {
    throw new Error("Для этого действия нужен выделенный текст.");
  }

  const contextBlock = buildContextBlock(context);

  if (pipeline === SELECTION_PIPELINE_TYPES.EXPLAIN_SELECTION) {
    return {
      messages: [
        {
          role: "system",
          content: `Ты LexEntropy, ведущий эксперт по праву Республики Казахстан. Твоя задача — профессиональный юридический анализ текстов.
Отвечай на русском языке в строгом деловом стиле.

ОГРАНИЧЕНИЯ:
- НЕ используй # для заголовков.
- НЕ используй горизонтальные разделители ---.
- НЕ используй кодовые блоки.
- Максимально точное цитирование и ссылки только на подтвержденные нормы.

ЛОГИКА ОТВЕТА:
1. СУТЬ НОРМЫ: Краткое изложение того, что регулирует этот фрагмент.
2. ПРАВОВЫЕ ПОСЛЕДСТВИЯ: Права, обязанности, запреты и юридические риски.
3. РЕКОМЕНДАЦИИ: Практические шаги или указание на смежные области права.
Если в тексте есть коллизия или неопределенность, укажи на это прямо.`,
        },
        {
          role: "user",
          content: `Контекст анализа:
${contextBlock}

Задание: проведи экспертный анализ выделенного фрагмента. Соблюдай структуру (Суть, Последствия, Рекомендации) без использования markdown-заголовков (#). Если номера статей не указаны в тексте и ты не уверен в них на 100%, не приводи их.`,
        },
      ],
      temperature: 0.2,
      maxTokens: 1000,
    };
  }

  if (pipeline === SELECTION_PIPELINE_TYPES.FIND_RELATED_NPA) {
    return {
      messages: [
        {
          role: "system",
          content: `Ты LexEntropy, эксперт-аналитик законодательства Республики Казахстан. Твоя задача — поиск иерархических и тематических связей между нормами права.
Отвечай на русском языке в деловом стиле.

ПРИОРИТЕТЫ ИЕРАРХИИ:
1. Конституционные законы и Кодексы (ГК РК, КоАП РК, Трудовой кодекс и т.д.).
2. Законы РК.
3. Подзаконные акты (Постановления Правительства, Приказы Министров).

ОГРАНИЧЕНИЯ:
- БЕЗ markdown-заголовков (#) и линий (---).
- Указывай только реально существующие НПА. Если сомневаешься в номере или дате, укажи только название ("Закон о...") и добавь пометку "Требует уточнения".`,
        },
        {
          role: "user",
          content: `Объект анализа:
${contextBlock}

Задание: Подбери 3-5 наиболее релевантных НПА или норм. 
Для каждой позиции укажи:
- Полное название НПА и его место в иерархии (Кодекс, Закон, Приказ).
- Конкретную связь с выделенным фрагментом (почему это важно проверить).
- По возможности, диапазон статей.
В конце добавь краткое резюме об основном векторе проверки. Не используй markdown-заголовки.`,
        },
      ],
      temperature: 0.2,
      maxTokens: 1200,
    };
  }

  throw new Error(`Неподдерживаемый сценарий выделения: ${pipeline}`);
}
