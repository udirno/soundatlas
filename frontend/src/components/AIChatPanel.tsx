'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { askAI, fetchAISuggestions, AISuggestion } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIChatPanelProps {
  onClose: () => void;
}

export default function AIChatPanel({ onClose }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchAISuggestions().then(setSuggestions).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(question?: string) {
    const text = (question ?? input).trim();
    if (!text || isLoading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);

    try {
      const response = await askAI(text);
      setMessages((prev) => [...prev, { role: 'assistant', content: response.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: "Sorry, I couldn't generate an answer. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className={`fixed z-50 flex flex-col rounded-xl shadow-2xl border border-gray-700 overflow-hidden bg-gray-900 text-white transition-all duration-200 ${isExpanded ? 'inset-4' : 'bottom-4 right-4 w-96 h-[580px]'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800 shrink-0">
        <span className="font-semibold text-sm">Ask AI</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="text-gray-400 hover:text-white transition-colors p-1 rounded"
            aria-label={isExpanded ? 'Collapse chat' : 'Expand chat'}
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors p-1 rounded"
            aria-label="Close chat"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && suggestions.length > 0 ? (
          <div className="flex flex-col gap-2 pt-2">
            <p className="text-xs text-gray-400 mb-1">Try asking:</p>
            {suggestions.map((chip, i) => (
              <button
                key={i}
                onClick={() => handleSend(chip.question)}
                disabled={isLoading}
                className="bg-blue-500/20 text-blue-300 rounded-full px-3 py-1.5 text-sm cursor-pointer hover:bg-blue-500/30 transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {chip.question}
              </button>
            ))}
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-100 whitespace-pre-wrap'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-700 text-gray-400 rounded-lg px-3 py-2 text-sm animate-pulse">
                  Thinking...
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-gray-700 bg-gray-800 px-3 py-2 flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Ask about your music library..."
          className="flex-1 bg-gray-700 text-white text-sm rounded-lg px-3 py-2 outline-none placeholder-gray-500 border border-gray-600 focus:border-blue-500 disabled:opacity-50"
        />
        <button
          onClick={() => handleSend()}
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm px-3 py-2 rounded-lg transition-colors shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  );
}
