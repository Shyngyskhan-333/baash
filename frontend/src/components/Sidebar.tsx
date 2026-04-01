import React, { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { chatWithAi } from '../services/api';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Loader2, X, MessageSquare } from 'lucide-react';

const AIChatPanel = () => {
  const { chatHistory, addChatHistory } = useStore();
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMessage = { role: 'user' as const, content: input };
    addChatHistory([userMessage]);
    setInput('');
    setIsLoading(true);
    try {
      const resp = await chatWithAi(input, chatHistory);
      addChatHistory([{ role: 'assistant', content: resp.answer, sources: resp.sources }]);
    } catch {
      addChatHistory([{ role: 'system', content: 'Ошибка соединения с сервером.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 w-12 h-12 bg-primary hover:bg-primaryHover rounded-full flex items-center justify-center shadow-2xl shadow-indigo-500/30 transition-all z-50"
      >
        <MessageSquare size={20} className="text-white" />
      </button>
    );
  }

  return (
    <div className="w-72 h-full flex flex-col border-l border-border bg-surface shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0">
          <Bot size={14} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-textMain">AI Помощник</h2>
          <p className="text-[10px] text-textMuted">Юрист по законодательству РК</p>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-textMuted hover:text-textMain transition">
          <X size={15} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatHistory.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-3">
              <Bot size={22} className="text-indigo-400" />
            </div>
            <p className="text-sm font-medium text-textMain mb-1">Чем могу помочь?</p>
            <p className="text-xs text-textMuted leading-relaxed">
              Задайте вопрос о казахстанском законодательстве. Я отвечаю со ссылками на конкретные статьи.
            </p>
          </div>
        )}

        {chatHistory.map((msg: any, idx: number) => (
          <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
              msg.role === 'user' ? 'bg-primary' : 'bg-surface border border-border'
            }`}>
              {msg.role === 'user' ? <User size={12} /> : <Bot size={12} className="text-indigo-400" />}
            </div>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
              msg.role === 'user'
                ? 'bg-primary text-white rounded-tr-none'
                : 'bg-surfaceHover text-textMain rounded-tl-none border border-border'
            }`}>
              <div className="prose prose-invert prose-xs max-w-none">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
              {msg.sources?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/10 text-[10px] text-textMuted">
                  📚 {msg.sources.map((s: any) => s.article).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-surface border border-border flex items-center justify-center shrink-0">
              <Bot size={12} className="text-indigo-400" />
            </div>
            <div className="bg-surfaceHover border border-border rounded-xl rounded-tl-none px-3 py-2.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border">
        <div className="flex items-end gap-2 bg-surfaceHover rounded-xl p-2.5 border border-border focus-within:border-indigo-500/50 transition">
          <textarea
            rows={1}
            className="flex-1 bg-transparent text-sm text-textMain placeholder-textMuted outline-none resize-none leading-relaxed"
            placeholder="Спросить ИИ..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all shrink-0 ${
              input.trim() && !isLoading
                ? 'bg-primary hover:bg-primaryHover text-white'
                : 'bg-surface text-textMuted cursor-not-allowed'
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
