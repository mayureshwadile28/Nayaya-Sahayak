import { useCallback, useRef, useState, useEffect } from 'react';
import type { AppScreen, ChatMessage, Language, Translations } from '../types';
import { askQuestion } from '../hooks/useApi';
import { sanitizeHtml, renderSafeMarkdown } from '../utils/sanitize';

interface ChatProps {
  t: (section: keyof Translations, key: string) => string;
  language: Language;
  documentId: string;
  messages: ChatMessage[];
  onAddMessage: (message: ChatMessage) => void;
  onNavigate: (screen: AppScreen) => void;
}

export default function Chat({
  t,
  language,
  documentId,
  messages,
  onAddMessage,
  onNavigate,
}: ChatProps) {
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isThinking) return;

    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    onAddMessage(userMessage);
    setInput('');
    setIsThinking(true);

    try {
      const result = await askQuestion(documentId, trimmed, language);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.answer,
        timestamp: new Date().toISOString(),
        citations: result.citations,
      };
      onAddMessage(assistantMessage);
    } catch {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'I apologize, but I couldn\'t process your question. Please try again.',
        timestamp: new Date().toISOString(),
      };
      onAddMessage(errorMessage);
    } finally {
      setIsThinking(false);
    }
  }, [input, isThinking, documentId, language, onAddMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <section className="animate-fade-in flex flex-col h-[calc(100vh-12rem)]" aria-labelledby="chat-heading">
      <div className="flex items-center justify-between mb-4">
        <h1 id="chat-heading" className="font-heading text-2xl font-bold text-white">
          💬 {t('chat', 'title')}
        </h1>
        <div className="flex gap-2">
          <button
            id="chat-back-btn"
            onClick={() => onNavigate('analysis')}
            className="btn-secondary text-sm"
            aria-label="Back to analysis"
          >
            ← {t('common', 'back')}
          </button>
          <button
            id="chat-rights-btn"
            onClick={() => onNavigate('rights')}
            className="btn-secondary text-sm"
            aria-label="View rights"
          >
            📋 Rights
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="disclaimer-banner text-xs mb-4" role="note">
        {t('chat', 'disclaimer')}
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto space-y-4 mb-4 p-2"
        role="log"
        aria-label="Chat conversation"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-4xl mb-3" role="img" aria-hidden="true">💬</p>
            <p>{t('analysis', 'ask_question')}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {[
                'What does the notice period clause mean?',
                'Is this security deposit amount legal?',
                'What are my rights here?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-1.5 rounded-full text-sm bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={msg.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'}
          >
            <div 
              className="text-sm leading-relaxed space-y-2 markdown-content"
              dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(msg.content) }}
            />
            {msg.citations && msg.citations.length > 0 && (
              <div className="mt-3 pt-2 border-t border-white/10">
                <p className="text-xs text-gray-400 mb-1">{t('chat', 'grounded_in')}</p>
                {msg.citations.map((citation, j) => (
                  <p key={j} className="text-xs text-primary-400">
                    📜 {sanitizeHtml(citation.source)}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}

        {isThinking && (
          <div className="chat-message-assistant" role="status">
            <div className="flex items-center gap-2">
              <span className="spinner" aria-hidden="true"></span>
              <span className="text-sm text-gray-400">{t('chat', 'thinking')}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3 items-end">
        <input
          ref={inputRef}
          id="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat', 'placeholder')}
          className="input-field flex-1"
          disabled={isThinking}
          aria-label={t('chat', 'placeholder')}
          maxLength={1000}
        />
        <button
          id="chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || isThinking}
          className="btn-primary px-6"
          aria-label={t('chat', 'send')}
        >
          {t('chat', 'send')}
        </button>
      </div>
    </section>
  );
}
