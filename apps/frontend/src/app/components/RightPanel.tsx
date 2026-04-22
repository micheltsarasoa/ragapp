import { useEffect, useRef, useState } from 'react';
import { Bot, Plus, Send, Loader2 } from 'lucide-react';
import { streamQuery } from '../../api/query';
import { useIdentity } from '../../hooks/useIdentity';
import { IconButton } from './ui/IconButton';

interface Message {
  type: 'bot' | 'user';
  content: string;
  sources?: string[];
  streaming?: boolean;
}

const WELCOME: Message = {
  type: 'bot',
  content: "Hello! I'm ready to answer questions about your knowledge base. Upload documents in the center panel, then ask me anything.",
};

export function RightPanel() {
  const { identity } = useIdentity();
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input,    setInput]    = useState('');
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || streaming || !identity) return;

    setInput('');
    setMessages((prev) => [...prev, { type: 'user', content: question }]);
    // Append an empty streaming bubble — tokens fill it as they arrive
    setMessages((prev) => [...prev, { type: 'bot', content: '', streaming: true }]);
    setStreaming(true);

    try {
      for await (const frame of streamQuery(question, identity.user_id)) {
        if (frame.token) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.type === 'bot') next[next.length - 1] = { ...last, content: last.content + frame.token };
            return next;
          });
        } else if (frame.sources) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.type === 'bot') next[next.length - 1] = { ...last, sources: frame.sources, streaming: false };
            return next;
          });
        } else if (frame.error) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.type === 'bot') next[next.length - 1] = { ...last, content: `Error: ${frame.error}`, streaming: false };
            return next;
          });
        }
      }
    } finally {
      // Clear streaming flag even if the generator exits without a done frame
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.type === 'bot' && last.streaming) next[next.length - 1] = { ...last, streaming: false };
        return next;
      });
      setStreaming(false);
    }
  };

  const userInitials = identity ? identity.access_key.slice(0, 2).toUpperCase() : 'U';
  const canSend = !!input.trim() && !!identity && !streaming;

  return (
    <div className="w-[440px] h-screen shrink-0 flex flex-col bg-surface-1">

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="h-16 px-5 flex items-center justify-between border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)' }}>
            <Bot size={18} color="white" />
          </div>
          <div>
            <p className="text-base font-semibold text-primary">AI Assistant</p>
            <p className="flex items-center gap-1 text-[11px] font-medium text-success">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-success" />
              RAG Active
            </p>
          </div>
        </div>
        <IconButton onClick={() => setMessages([WELCOME])} title="New chat">
          <Plus size={20} />
        </IconButton>
      </div>

      {/* ── Messages ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 animate-fade-up ${msg.type === 'user' ? 'flex-row-reverse' : ''}`}
            style={{ animationDelay: `${Math.min(i * 30, 120)}ms` }}
          >
            {/* Avatar */}
            <div className="shrink-0">
              {msg.type === 'bot' ? (
                <div className="w-7 h-7 rounded-full flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)' }}>
                  <Bot size={14} color="white" />
                </div>
              ) : (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white text-xs font-medium">
                  {userInitials}
                </div>
              )}
            </div>

            {/* Bubble */}
            <div className={`flex-1 ${msg.type === 'user' ? 'flex flex-col items-end' : ''}`}>
              <div
                className="px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
                style={{
                  background:    msg.type === 'bot' ? 'var(--surface-l2)' : 'var(--accent-blue)',
                  color:         msg.type === 'bot' ? 'var(--text-primary)' : 'white',
                  borderRadius:  msg.type === 'bot' ? '0 12px 12px 12px' : '12px 0 12px 12px',
                  maxWidth: '85%',
                }}
              >
                {msg.content}
                {msg.streaming && !msg.content && (
                  <Loader2 size={14} className="animate-spin inline-block" />
                )}
              </div>

              {/* Source badges */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.sources.map((src, j) => (
                    <span
                      key={j}
                      className="px-2 py-0.5 rounded text-xs text-muted-fg bg-surface-2 border border-border-subtle"
                    >
                      {src}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* ── Input ─────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <div className="rounded-xl px-4 py-3 flex items-center gap-3 border border-border-subtle bg-surface-2 min-h-[48px]">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={identity ? 'Ask a question about your documents...' : 'Connecting...'}
            disabled={!identity || streaming}
            className="flex-1 bg-transparent outline-none text-sm text-primary placeholder:text-muted-fg"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-colors
              ${canSend ? 'bg-accent hover:bg-accent-hover' : 'bg-surface-3'}`}
          >
            {streaming
              ? <Loader2 size={16} color="white" className="animate-spin" />
              : <Send size={16} color="white" />}
          </button>
        </div>
        <p className="text-center mt-2 text-[11px] text-muted-fg">
          AI can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}
