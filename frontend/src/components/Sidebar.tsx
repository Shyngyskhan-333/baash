import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bookmark, Bot, Loader2, MessageSquare, Send, Trash2, User, X } from 'lucide-react';
import { chatWithAi } from '../services/api';
import { useStore } from '../store/useStore';

const AIChatPanel = () => {
  const { chatHistory, addChatHistory, activeScope, clearChatHistory, pendingMessage, setPendingMessage } = useStore();
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  const sendMessage = useCallback(async (text: string) => {
    const userMessage = { role: 'user' as const, content: text };
    const currentHistory = useStore.getState().chatHistory;
    addChatHistory([userMessage]);
    setIsLoading(true);

    try {
      const response = await chatWithAi(text, currentHistory, undefined, 'general', activeScope);
      addChatHistory([{ role: 'assistant', content: response.answer, sources: response.sources }]);
    } catch (requestError: unknown) {
      const error = requestError as { response?: { data?: { detail?: string; answer?: string } }; message?: string };
      const message =
        error.response?.data?.detail ||
        error.response?.data?.answer ||
        error.message ||
        'Неизвестная ошибка сервера';

      addChatHistory([{ role: 'system', content: `Ошибка: ${message}` }]);
    } finally {
      setIsLoading(false);
    }
  }, [activeScope, addChatHistory]);

  useEffect(() => {
    if (pendingMessage && !isLoading) {
      setIsOpen(true);
      const message = pendingMessage;
      setPendingMessage(null);
      sendMessage(message);
    }
  }, [isLoading, pendingMessage, sendMessage, setPendingMessage]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) {
      return;
    }

    const text = input;
    setInput('');
    await sendMessage(text);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 w-12 h-12 bg-primary hover:bg-primaryHover rounded-full flex items-center justify-center shadow-lg shadow-primaryShadow/20 transition-all z-50 text-surface"
      >
        <MessageSquare size={20} />
      </button>
    );
  }

  return (
    <div className="w-72 h-full flex flex-col border-l border-border bg-surface shrink-0">
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/80 to-primaryStrong/80 flex items-center justify-center shrink-0">
            <Bot size={14} className="text-surface" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-display font-bold text-textMain">AI Ассистент</h2>
            <p className="text-[10px] text-textMuted uppercase tracking-wider font-medium">Правовой контекст</p>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-textMuted hover:text-textMain transition">
            <X size={15} />
          </button>
        </div>

        <div className="flex items-center justify-between bg-surfaceHover rounded-lg px-2.5 py-1.5 border border-border">
          <div className="flex items-center gap-1.5">
            <Bookmark size={11} className="text-primary" />
            <span className="text-[10px] text-textSub font-medium font-mono uppercase tracking-tight">
              {activeScope.length > 0 ? `Scope: ${activeScope.length}` : 'Global'}
            </span>
          </div>
          <button
            onClick={() => clearChatHistory()}
            className="text-textDim hover:text-riskHigh transition-colors p-0.5"
            title="Очистить чат"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatHistory.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <div className="w-12 h-12 rounded-xl bg-primary/5 border border-primary/10 flex items-center justify-center mb-3">
              <Bot size={22} className="text-primary" />
            </div>
            <p className="text-sm font-display font-bold text-textMain mb-1">Чем могу помочь?</p>
            <p className="text-xs text-textMuted leading-relaxed">
              Задайте вопрос о законодательстве. Я помогу найти релевантные статьи и нормы.
            </p>
          </div>
        )}

        {chatHistory.map((message: { role: string; content: string; sources?: { article: string }[] }, index: number) => (
          <div key={index} className={`flex gap-2 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div
              className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
                message.role === 'user' ? 'bg-primary/20' : 'bg-surfaceAlt border border-border'
              }`}
            >
              {message.role === 'user' ? <User size={12} className="text-primary" /> : <Bot size={12} className="text-primary" />}
            </div>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                message.role === 'user'
                  ? 'bg-primary/15 text-textMain rounded-tr-none border border-primary/10'
                  : 'bg-surfaceHover text-textSub rounded-tl-none border border-border'
              }`}
            >
              <div className="prose prose-xs max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border text-[10px] text-primary/60 uppercase font-bold tracking-tight font-mono">
                  Источники: {message.sources.map((source) => source.article).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-md bg-surfaceAlt border border-border flex items-center justify-center shrink-0">
              <Bot size={12} className="text-primary" />
            </div>
            <div className="bg-surfaceHover border border-border rounded-xl rounded-tl-none px-3 py-2.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t border-border">
        <div className="flex items-end gap-2 bg-surfaceHover rounded-xl p-2.5 border border-border input-glow transition">
          <textarea
            rows={1}
            className="flex-1 bg-transparent text-sm text-textMain placeholder-textDim outline-none resize-none leading-relaxed py-1 font-body"
            placeholder="Спросите о законе..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all shrink-0 ${
              input.trim() && !isLoading ? 'bg-primary hover:bg-primaryHover text-surface' : 'bg-surfaceAlt text-textDim cursor-not-allowed'
            }`}
          >
            {isLoading ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIChatPanel;