import { useEffect, useState } from 'react';
import { AlignLeft, Columns, EyeOff, GitMerge, Layers, Loader2 } from 'lucide-react';
import { diffDocuments, fetchDocument, previewDocument } from '../services/api';
import { useStore } from '../store/useStore';

interface DiffHunk {
  type: string;
  line_number: number;
  old_text?: string;
  new_text?: string;
}

interface DiffResult {
  hunks: DiffHunk[];
  stats: {
    added: number;
    removed: number;
    changed: number;
  };
  ai_summary: string;
}

interface VersionMeta {
  version_id: string;
  date: string;
  status: string;
}

const stopwords = new Set([
  'и', 'в', 'во', 'на', 'но', 'а', 'что', 'как', 'к', 'ко', 'из', 'за', 'по', 'при', 'для', 'это', 'то',
  'не', 'ни', 'с', 'со', 'у', 'о', 'об', 'от', 'до', 'над', 'под', 'про', 'ли', 'или', 'так', 'же',
  'бы', 'быть', 'был', 'были', 'есть', 'ее', 'его', 'их', 'мы', 'вы', 'они', 'он', 'она', 'оно',
  'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were', 'has', 'have', 'had',
]);

function isCurrentLikeStatus(status: string) {
  const value = status.toLowerCase();
  return value === 'current' || value === 'effective';
}

function pickOlderAndNewer(versions: VersionMeta[]) {
  if (versions.length === 0) {
    return { older: null as VersionMeta | null, newer: null as VersionMeta | null };
  }

  const newer = versions.find((version) => isCurrentLikeStatus(version.status)) ?? versions[0];
  let older = versions.find((version) => version.status.toLowerCase() === 'archived') ?? null;

  if (!older && versions.length >= 2) {
    older = versions.find((version) => version.version_id !== newer.version_id) ?? null;
  }

  if (older?.version_id === newer.version_id) {
    older = null;
  }

  return { older, newer };
}

function getVersionLabel(version: VersionMeta) {
  const datePart = version.date || 'без даты';
  const statusPart = version.status || 'unknown';
  return `${datePart} • ${statusPart} • ${version.version_id}`;
}

function getTextMetrics(text: string) {
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const lines = text.trim() ? text.trim().split(/\r?\n/).length : 0;
  return { chars, words, lines };
}

function formatDelta(before: number, after: number) {
  if (before === 0 && after === 0) {
    return '0%';
  }
  if (before === 0) {
    return '+100%';
  }
  const delta = Math.round(((after - before) / before) * 100);
  return `${delta > 0 ? '+' : ''}${delta}%`;
}

function extractWords(text: string) {
  const matches = text.toLowerCase().match(/[a-zа-яё0-9]+/gi) || [];
  return matches.filter((word) => word.length >= 4 && !stopwords.has(word));
}

function getKeywordDelta(oldText: string, newText: string) {
  const oldMap = new Map<string, number>();
  const newMap = new Map<string, number>();

  for (const word of extractWords(oldText)) {
    oldMap.set(word, (oldMap.get(word) || 0) + 1);
  }

  for (const word of extractWords(newText)) {
    newMap.set(word, (newMap.get(word) || 0) + 1);
  }

  const allWords = new Set([...oldMap.keys(), ...newMap.keys()]);
  const deltas: Array<{ word: string; delta: number }> = [];

  for (const word of allWords) {
    const delta = (newMap.get(word) || 0) - (oldMap.get(word) || 0);
    if (delta !== 0) {
      deltas.push({ word, delta });
    }
  }

  return {
    added: deltas.filter((item) => item.delta > 0).sort((a, b) => b.delta - a.delta).slice(0, 6),
    removed: deltas.filter((item) => item.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 6),
  };
}

function getKeywordDeltaFromHunks(hunks: DiffHunk[]) {
  const oldText = hunks.map((hunk) => hunk.old_text || '').join('\n');
  const newText = hunks.map((hunk) => hunk.new_text || '').join('\n');
  return getKeywordDelta(oldText, newText);
}

function highlightKeywords(text: string, keywords: string[]) {
  if (!text || keywords.length === 0) {
    return [{ text, highlight: false }] as Array<{ text: string; highlight: boolean }>;
  }

  const uniqueKeywords = [...new Set(keywords)].sort((a, b) => b.length - a.length);
  const escaped = uniqueKeywords.map((keyword) => keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(^|[^\\p{L}\\p{N}])(${escaped.join('|')})(?=[^\\p{L}\\p{N}]|$)`, 'giu');
  const parts: Array<{ text: string; highlight: boolean }> = [];
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const matchIndex = match.index ?? 0;
    const prefix = match[1] ?? '';
    const word = match[2] ?? '';
    const start = matchIndex + prefix.length;
    const end = start + word.length;

    if (start > lastIndex) {
      parts.push({ text: text.slice(lastIndex, start), highlight: false });
    }

    if (prefix) {
      parts.push({ text: prefix, highlight: false });
    }

    parts.push({ text: text.slice(start, end), highlight: true });
    lastIndex = end;
  }

  if (lastIndex < text.length) {
    parts.push({ text: text.slice(lastIndex), highlight: false });
  }

  return parts;
}

const DiffPage = () => {
  const { activeScope, diffState, setDiffState } = useStore();
  const { textA, textB, result, mode, hideUnchanged, showKeywords } = diffState;

  const [loading, setLoading] = useState(false);
  const [isAutoLoading, setIsAutoLoading] = useState(false);
  const [error, setError] = useState('');
  const [versionNotice, setVersionNotice] = useState('');
  const [docId, setDocId] = useState<string | null>(null);
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [versionA, setVersionA] = useState('');
  const [versionB, setVersionB] = useState('');
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>({});
  const [showThink, setShowThink] = useState(false);

  const isMulti = activeScope.length > 1;

  useEffect(() => {
    if (isMulti) {
      setDocId(null);
      setVersions([]);
      setVersionA('');
      setVersionB('');
      setVersionNotice('');
      setError('Для сравнения выберите один документ.');
      return;
    }

    if (activeScope.length !== 1) {
      setDocId(null);
      setVersions([]);
      setVersionA('');
      setVersionB('');
      setVersionNotice('');
      setError('');
      return;
    }

    const targetDocId = activeScope[0];
    setDocId(targetDocId);
    setError('');

    let isMounted = true;

    const loadVersions = async () => {
      setIsAutoLoading(true);
      setVersionNotice('');

      try {
        const meta = await previewDocument(targetDocId);
        if (!isMounted) {
          return;
        }

        const loadedVersions: VersionMeta[] = Array.isArray(meta.versions) ? meta.versions : [];
        setVersions(loadedVersions);

        const { older, newer } = pickOlderAndNewer(loadedVersions);
        if (!newer) {
          setError('Не удалось определить доступные версии документа.');
          return;
        }

        if (!older) {
          setVersionA('');
          setVersionB(newer.version_id);
          setVersionNotice(
            'В архиве доступна только одна редакция этого НПА. Старую версию загрузите с Адилет или выберите другой документ.',
          );

          const currentDoc = await fetchDocument(newer.version_id);
          if (!isMounted) {
            return;
          }

          setDiffState({
            textA: '',
            textB: currentDoc?.text ?? '',
            result: null,
          });
          return;
        }

        setVersionA(older.version_id);
        setVersionB(newer.version_id);

        const [oldDoc, newDoc] = await Promise.all([
          fetchDocument(older.version_id),
          fetchDocument(newer.version_id),
        ]);

        if (!isMounted) {
          return;
        }

        setDiffState({
          textA: oldDoc?.text ?? '',
          textB: newDoc?.text ?? '',
          result: null,
        });
      } catch (loadError) {
        console.error('Failed to load diff versions', loadError);
        if (isMounted) {
          setError('Не удалось загрузить версии документа для сравнения.');
        }
      } finally {
        if (isMounted) {
          setIsAutoLoading(false);
        }
      }
    };

    loadVersions();

    return () => {
      isMounted = false;
    };
  }, [activeScope, isMulti, setDiffState]);

  const loadSelectedVersions = async () => {
    if (!versionA || !versionB) {
      return;
    }

    if (versionA === versionB) {
      setError('Выберите две разные редакции.');
      return;
    }

    setIsAutoLoading(true);
    setError('');
    setVersionNotice('');

    try {
      const [oldDoc, newDoc] = await Promise.all([
        fetchDocument(versionA),
        fetchDocument(versionB),
      ]);

      setDiffState({
        textA: oldDoc?.text ?? '',
        textB: newDoc?.text ?? '',
        result: null,
      });
    } catch (loadError) {
      console.error('Failed to fetch selected versions', loadError);
      setError('Не удалось загрузить выбранные версии.');
    } finally {
      setIsAutoLoading(false);
    }
  };

  const handleDiff = async () => {
    if (!textA.trim() || !textB.trim()) {
      return;
    }

    if (textA.trim() === textB.trim()) {
      setError('Тексты совпадают. Выберите разные редакции документа.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await diffDocuments(textA, textB);
      setDiffState({ result: data });
    } catch (requestError: unknown) {
      const errorWithResponse = requestError as { response?: { data?: { detail?: string } }; message?: string };
      setError(errorWithResponse.response?.data?.detail || errorWithResponse.message || 'Ошибка сравнения.');
    } finally {
      setLoading(false);
    }
  };

  const renderDiff = (
    diffResult: DiffResult | null,
    options?: {
      showClose?: boolean;
      onClose?: () => void;
      metrics?: { aText: string; bText: string };
      keyPrefix?: string;
    },
  ) => {
    if (!diffResult) {
      return null;
    }

    const thinkMatch = diffResult.ai_summary?.match(/<think>([\s\S]*?)<\/think>/i);
    const thinkContent = thinkMatch?.[1]?.trim() ?? '';
    const summaryText = diffResult.ai_summary
      ? diffResult.ai_summary.replace(/<think>[\s\S]*?<\/think>/gi, '').trim()
      : '';
    const visibleHunks = hideUnchanged
      ? diffResult.hunks.filter((hunk) => hunk.type !== 'unchanged')
      : diffResult.hunks;
    const keywordDelta = getKeywordDeltaFromHunks(visibleHunks);
    const addedKeywords = keywordDelta.added.map((item) => item.word);
    const removedKeywords = keywordDelta.removed.map((item) => item.word);
    const keyPrefix = options?.keyPrefix ? `${options.keyPrefix}-` : '';

    return (
      <div className="flex-1 flex flex-col overflow-hidden bg-surface border border-border rounded-2xl">
        <div className="p-5 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex gap-4 font-mono text-sm">
            <span className="text-riskLowText font-bold bg-riskLow/10 px-3 py-1 rounded border border-riskLow/20">
              + {diffResult.stats.added}
            </span>
            <span className="text-riskHighText font-bold bg-riskHigh/10 px-3 py-1 rounded border border-riskHigh/20">
              - {diffResult.stats.removed}
            </span>
            <span className="text-riskMediumText font-bold bg-riskMedium/10 px-3 py-1 rounded border border-riskMedium/20">
              ~ {diffResult.stats.changed}
            </span>
            {options?.metrics && (() => {
              const oldMetrics = getTextMetrics(options.metrics.aText);
              const newMetrics = getTextMetrics(options.metrics.bText);
              return (
                <span className="text-textDim bg-surfaceAlt px-3 py-1 rounded border border-border/70">
                  симв.: {oldMetrics.chars} → {newMetrics.chars} ({formatDelta(oldMetrics.chars, newMetrics.chars)}) | строки:{' '}
                  {oldMetrics.lines} → {newMetrics.lines} | слова: {oldMetrics.words} → {newMetrics.words}
                </span>
              );
            })()}
          </div>
          {options?.showClose && options.onClose && (
            <button
              className="text-textMuted hover:text-textMain transition flex items-center gap-2 text-sm bg-surfaceAlt px-4 py-2 rounded-lg border border-border font-mono"
              onClick={options.onClose}
            >
              Закрыть diff
            </button>
          )}
        </div>

        {showKeywords && (
          <div className="px-5 py-3 border-b border-border bg-surfaceAlt/40">
            <div className="flex flex-wrap gap-2 text-xs font-mono text-textDim">
              <span className="uppercase tracking-wider text-textSub">Ключевые слова</span>
              <span>+</span>
              {keywordDelta.added.length > 0 ? (
                keywordDelta.added.map((item) => (
                  <span key={`add-${item.word}`} className="px-2 py-0.5 rounded bg-riskLow/10 text-riskLowText border border-riskLow/20">
                    {item.word} ({item.delta})
                  </span>
                ))
              ) : (
                <span className="text-textDim">нет</span>
              )}
              <span className="mx-1 text-textDim">|</span>
              <span>-</span>
              {keywordDelta.removed.length > 0 ? (
                keywordDelta.removed.map((item) => (
                  <span key={`remove-${item.word}`} className="px-2 py-0.5 rounded bg-riskHigh/10 text-riskHighText border border-riskHigh/20">
                    {item.word} ({Math.abs(item.delta)})
                  </span>
                ))
              ) : (
                <span className="text-textDim">нет</span>
              )}
            </div>
          </div>
        )}

        <div className="p-5 border-b border-border bg-primary/[0.03]">
          <div className="flex items-start gap-3">
            <Layers className="text-primary mt-0.5 shrink-0" size={18} />
            <div>
              <h3 className="font-display font-bold text-textMain mb-1 text-sm">AI резюме сравнения</h3>
              {summaryText && <p className="text-textSub text-sm leading-relaxed">{summaryText}</p>}
              {thinkContent && (
                <div className="mt-3">
                  <button
                    className="text-xs font-mono text-textMuted hover:text-textMain transition"
                    onClick={() => setShowThink((value) => !value)}
                  >
                    {showThink ? 'Скрыть рассуждения' : 'Показать рассуждения'}
                  </button>
                  {showThink && (
                    <div className="mt-2 text-xs text-textMuted whitespace-pre-wrap bg-surfaceAlt/50 border border-border rounded-lg p-3">
                      {thinkContent}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className={`flex-1 overflow-y-auto font-mono text-sm leading-relaxed ${mode === 'split' ? 'flex flex-col gap-2' : 'block'}`}>
          {visibleHunks.map((hunk, index) => {
            if (mode === 'split') {
              return (
                <div key={`${keyPrefix}split-${index}`} className="flex flex-col w-full rounded-xl overflow-hidden">
                  <div className={`flex-1 p-4 ${hunk.type === 'removed' || hunk.type === 'changed' ? 'bg-riskHigh/[0.04]' : ''}`}>
                    <div className="text-textDim mb-2 text-[10px] select-none font-mono">
                      {hunk.type === 'removed' || hunk.type === 'changed' ? '-' : ' '} L{hunk.line_number}
                    </div>
                    <div
                      className={`whitespace-pre-wrap text-textMuted ${expandedBlocks[`${keyPrefix}old-${index}`] ? '' : 'max-h-40 overflow-hidden'} cursor-pointer`}
                      onClick={() =>
                        setExpandedBlocks((previous) => ({
                          ...previous,
                          [`${keyPrefix}old-${index}`]: !previous[`${keyPrefix}old-${index}`],
                        }))
                      }
                      title="Нажмите, чтобы раскрыть или свернуть"
                    >
                      {(showKeywords
                        ? highlightKeywords(hunk.old_text || '', removedKeywords)
                        : [{ text: hunk.old_text || '', highlight: false }]).map((part, partIndex) => (
                        <span key={`${keyPrefix}old-part-${index}-${partIndex}`} className={part.highlight ? 'bg-riskHigh/20 text-riskHighText' : ''}>
                          {part.text}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className={`flex-1 p-4 border-t border-border/40 ${hunk.type === 'added' || hunk.type === 'changed' ? 'bg-riskLow/[0.04]' : ''}`}>
                    <div className="text-textDim mb-2 text-[10px] select-none font-mono">
                      {hunk.type === 'added' || hunk.type === 'changed' ? '+' : ' '} L{hunk.line_number}
                    </div>
                    <div
                      className={`whitespace-pre-wrap text-textMuted ${expandedBlocks[`${keyPrefix}new-${index}`] ? '' : 'max-h-40 overflow-hidden'} cursor-pointer`}
                      onClick={() =>
                        setExpandedBlocks((previous) => ({
                          ...previous,
                          [`${keyPrefix}new-${index}`]: !previous[`${keyPrefix}new-${index}`],
                        }))
                      }
                      title="Нажмите, чтобы раскрыть или свернуть"
                    >
                      {(showKeywords
                        ? highlightKeywords(hunk.new_text || '', addedKeywords)
                        : [{ text: hunk.new_text || '', highlight: false }]).map((part, partIndex) => (
                        <span key={`${keyPrefix}new-part-${index}-${partIndex}`} className={part.highlight ? 'bg-riskLow/20 text-riskLowText' : ''}>
                          {part.text}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            }

            return (
              <div key={`${keyPrefix}unified-${index}`} className="rounded-lg overflow-hidden mb-2 last:mb-0">
                {hunk.old_text && (
                  <div className="flex">
                    <div className="w-14 text-center text-textDim bg-riskHigh/5 py-2 select-none text-xs">-{hunk.line_number}</div>
                    <div
                      className={`flex-1 p-2 whitespace-pre-wrap bg-riskHigh/[0.04] text-riskHighText/90 ${expandedBlocks[`${keyPrefix}old-u-${index}`] ? '' : 'max-h-40 overflow-hidden'} cursor-pointer`}
                      onClick={() =>
                        setExpandedBlocks((previous) => ({
                          ...previous,
                          [`${keyPrefix}old-u-${index}`]: !previous[`${keyPrefix}old-u-${index}`],
                        }))
                      }
                      title="Нажмите, чтобы раскрыть или свернуть"
                    >
                      {(showKeywords
                        ? highlightKeywords(hunk.old_text, removedKeywords)
                        : [{ text: hunk.old_text, highlight: false }]).map((part, partIndex) => (
                        <span key={`${keyPrefix}old-u-part-${index}-${partIndex}`} className={part.highlight ? 'bg-riskHigh/20 text-riskHighText' : ''}>
                          {part.text}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {hunk.new_text && (
                  <div className="flex">
                    <div className="w-14 text-center text-textDim bg-riskLow/5 py-2 select-none text-xs">+{hunk.line_number}</div>
                    <div
                      className={`flex-1 p-2 whitespace-pre-wrap bg-riskLow/[0.04] text-riskLowText/90 ${expandedBlocks[`${keyPrefix}new-u-${index}`] ? '' : 'max-h-40 overflow-hidden'} cursor-pointer`}
                      onClick={() =>
                        setExpandedBlocks((previous) => ({
                          ...previous,
                          [`${keyPrefix}new-u-${index}`]: !previous[`${keyPrefix}new-u-${index}`],
                        }))
                      }
                      title="Нажмите, чтобы раскрыть или свернуть"
                    >
                      {(showKeywords
                        ? highlightKeywords(hunk.new_text, addedKeywords)
                        : [{ text: hunk.new_text, highlight: false }]).map((part, partIndex) => (
                        <span key={`${keyPrefix}new-u-part-${index}-${partIndex}`} className={part.highlight ? 'bg-riskLow/20 text-riskLowText' : ''}>
                          {part.text}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col bg-background overflow-hidden relative h-full">
      <div className="px-10 pt-24 pb-4 shrink-0">
        {error && (
          <div className="mb-4 p-3 bg-riskHigh/10 border border-riskHigh/20 rounded-lg text-riskHighText font-medium text-sm">
            {error}
          </div>
        )}

        {versionNotice && (
          <div className="mb-4 p-3 bg-primary/5 border border-primary/20 rounded-lg text-textSub text-sm">
            {versionNotice}
          </div>
        )}

        <div className="flex justify-between items-center gap-4">
          <div>
            <h1 className="text-3xl font-display font-bold flex items-center gap-3">
              <GitMerge className="text-primary" /> Сравнение редакций
            </h1>
            <p className="text-textMuted mt-1 text-sm">
              Сравнивайте старую и новую версии как в Git: split/unified, метрики и AI-резюме.
            </p>
          </div>

          {result && (
            <div className="flex items-center gap-2">
              <button
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border transition ${
                  hideUnchanged ? 'bg-surfaceAlt text-textMain border-border' : 'text-textMuted hover:text-textSub border-border/60'
                }`}
                onClick={() => setDiffState({ hideUnchanged: !hideUnchanged })}
              >
                <EyeOff size={16} /> {hideUnchanged ? 'Показывать unchanged' : 'Скрывать unchanged'}
              </button>
              <button
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium border transition ${
                  showKeywords ? 'bg-surfaceAlt text-textMain border-border' : 'text-textMuted hover:text-textSub border-border/60'
                }`}
                onClick={() => setDiffState({ showKeywords: !showKeywords })}
              >
                Ключевые слова
              </button>
              <div className="flex bg-surface rounded-lg p-1 border border-border">
                <button
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
                    mode === 'split' ? 'bg-surfaceAlt text-textMain' : 'text-textMuted hover:text-textSub'
                  }`}
                  onClick={() => setDiffState({ mode: 'split' })}
                >
                  <Columns size={16} /> Split
                </button>
                <button
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
                    mode === 'unified' ? 'bg-surfaceAlt text-textMain' : 'text-textMuted hover:text-textSub'
                  }`}
                  onClick={() => setDiffState({ mode: 'unified' })}
                >
                  <AlignLeft size={16} /> Unified
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {!result ? (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-6xl mx-auto px-10 pb-10 overflow-auto">
          {docId && versions.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-4 grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] uppercase tracking-wider font-mono text-textMuted">Старая версия</label>
                <select
                  className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-textMain outline-none focus:border-primary/40"
                  value={versionA}
                  onChange={(event) => setVersionA(event.target.value)}
                >
                  <option value="">Выберите архивную версию</option>
                  {versions.map((version) => (
                    <option key={`old-${version.version_id}`} value={version.version_id}>
                      {getVersionLabel(version)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] uppercase tracking-wider font-mono text-textMuted">Новая версия</label>
                <select
                  className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-textMain outline-none focus:border-primary/40"
                  value={versionB}
                  onChange={(event) => setVersionB(event.target.value)}
                >
                  <option value="">Выберите новую версию</option>
                  {versions.map((version) => (
                    <option key={`new-${version.version_id}`} value={version.version_id}>
                      {getVersionLabel(version)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <button
                  className="w-full md:w-auto px-4 py-2 rounded-lg border border-primary/25 text-primary hover:bg-primary/10 transition text-sm font-medium disabled:opacity-50"
                  onClick={loadSelectedVersions}
                  disabled={isAutoLoading || !versionA || !versionB || versionA === versionB}
                >
                  Загрузить версии
                </button>
              </div>
            </div>
          )}

          <div className="flex flex-1 gap-6 w-full bg-surface rounded-2xl p-6 border border-border min-h-[400px]">
            <div className="flex-1 flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-textMuted font-mono">Старая редакция</label>
              <textarea
                className="flex-1 bg-background border border-border rounded-xl p-4 text-textMain resize-none outline-none focus:border-primary/30 transition font-mono text-sm leading-relaxed"
                placeholder="Текст старой редакции загрузится автоматически..."
                value={textA}
                onChange={(event) => setDiffState({ textA: event.target.value })}
              />
            </div>

            <div className="flex-1 flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-textMuted font-mono">Новая редакция</label>
              <textarea
                className="flex-1 bg-background border border-border rounded-xl p-4 text-textMain resize-none outline-none focus:border-primary/30 transition font-mono text-sm leading-relaxed"
                placeholder="Текст новой редакции загрузится автоматически..."
                value={textB}
                onChange={(event) => setDiffState({ textB: event.target.value })}
              />
            </div>
          </div>

          <div className="text-center">
            <button
              className="px-8 py-3.5 bg-primary hover:bg-primaryHover text-surface font-bold text-sm rounded-full shadow-lg shadow-primaryShadow/10 transition transform hover:scale-[1.02] font-display tracking-wide disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={handleDiff}
              disabled={loading || isAutoLoading || !textA.trim() || !textB.trim()}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="animate-spin" size={16} /> Сравниваем...
                </span>
              ) : (
                'Сравнить'
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden mx-10 mb-6">
          {renderDiff(result as DiffResult, {
            showClose: true,
            onClose: () => setDiffState({ result: null }),
            metrics: { aText: textA, bText: textB },
          })}
        </div>
      )}
    </div>
  );
};

export default DiffPage;