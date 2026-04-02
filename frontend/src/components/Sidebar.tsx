import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { chatWithAi } from '../services/api';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Loader2, X, MessageSquare, Trash2, History } from 'lucide-react';

const AIChatPanel = () => {
  const { chatHistory, addChatHistory, activeScope, clearChatHistory, pendingMessage, setPendingMessage } = useStore();
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  // Watch for pending messages from other components (e.g. "Спросить AI" button)
  useEffect(() => {
    if (pendingMessage && !isLoading) {
      setIsOpen(true); // ensure panel is visible
      const msg = pendingMessage;
      setPendingMessage(null); // clear immediately to prevent re-trigger
      sendMessage(msg);
    }
  }, [pendingMessage]);

  const sendMessage = async (text: string) => {
    const userMessage = { role: 'user' as const, content: text };
    const currentHistory = useStore.getState().chatHistory;
    addChatHistory([userMessage]);
    setIsLoading(true);
    try {
      const resp = await chatWithAi(text, currentHistory, undefined, 'general', activeScope);
      addChatHistory([{ role: 'assistant', content: resp.answer, sources: resp.sources }]);
    } catch (err: any) {
      console.error('[CHAT_API_ERROR]', err);
      const errMsg = err.response?.data?.detail 
        || err.response?.data?.answer 
        || err.message 
        || 'Неизвестная ошибка сервера';
      addChatHistory([{ role: 'system', content: `❌ Ошибка запроса: ${errMsg}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const text = input;
    setInput('');
    await sendMessage(text);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 w-12 h-12 bg-primary hover:bg-primaryHover rounded-full flex items-center justify-center shadow-lg transition-all z-50 text-white"
      >
        <MessageSquare size={20} />
      </button>
    );
  }

  return (
    <div className="w-72 h-full flex flex-col border-l border-border bg-surface shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <Bot size={14} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-serif font-bold text-textMain">AI Assistant</h2>
            <p className="text-[10px] text-textMuted uppercase tracking-wider font-semibold">Legal Context</p>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-textMuted hover:text-textMain transition">
            <X size={15} />
          </button>
        </div>

        {/* Global Scope & Actions Indicator */}
        <div className="flex items-center justify-between bg-surfaceHover rounded-lg px-2 py-1.5 border border-border">
          <div className="flex items-center gap-1.5">
            <History size={11} className="text-primary" />
            <span className="text-[10px] text-textSub font-medium uppercase tracking-tight">
              Scope: {activeScope.length || 'Global'}
            </span>
          </div>
          <button 
            onClick={() => clearChatHistory?.()}
            className="text-textMuted hover:text-red-500 transition-colors p-0.5"
            title="Clear Chat History"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatHistory.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <div className="w-12 h-12 rounded-xl bg-primary/5 border border-primary/10 flex items-center justify-center mb-3">
              <Bot size={22} className="text-primary" />
            </div>
            <p className="text-sm font-serif font-bold text-textMain mb-1">How can I help?</p>
            <p className="text-xs text-textMuted leading-relaxed">
              Ask about legislation or case law. I'll provide references to the relevant articles.
            </p>
          </div>
        )}

        {chatHistory.map((msg: any, idx: number) => (
          <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
              msg.role === 'user' ? 'bg-primary' : 'bg-white border border-border text-primary'
            }`}>
              {msg.role === 'user' ? <User size={12} className="text-white" /> : <Bot size={12} />}
            </div>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
              msg.role === 'user'
                ? 'bg-primary text-white rounded-tr-none'
                : 'bg-surfaceHover text-textMain rounded-tl-none border border-border shadow-sm'
            }`}>
              <div className={`prose ${msg.role === 'user' ? 'prose-invert' : 'prose-sm'} prose-xs max-w-none`}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
              {msg.sources?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border text-[10px] text-textMuted uppercase font-bold tracking-tight">
                  Sources: {msg.sources.map((s: any) => s.article).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-md bg-white border border-border flex items-center justify-center shrink-0">
              <Bot size={12} className="text-primary" />
            </div>
            <div className="bg-surfaceHover border border-border rounded-xl rounded-tl-none px-3 py-2.5 flex items-center gap-1.5 shadow-sm">
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border">
        <div className="flex items-end gap-2 bg-white rounded-xl p-2.5 border border-border input-glow transition">
          <textarea
            rows={1}
            className="flex-1 bg-transparent text-sm text-textMain placeholder-textMuted outline-none resize-none leading-relaxed py-1"
            placeholder="Ask AI..."
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
