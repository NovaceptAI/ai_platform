import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './ChatBot.css';

const SAMPLE_QA = [
  {
    q: 'How do I navigate between stages?',
    a: 'Use the left navigation and the top Navbar. The stages are Create, Discover, Organize, Collaborate, and Master.'
  },
  {
    q: 'Where can I find the AI tools?',
    a: 'Open the Discover or Master stages for specialized tools, or check AI Tools like ChronoAI, Document Analyzer, and TreeView from the routes.'
  },
  {
    q: 'How do I access my Vault?',
    a: 'Go to Vault from the main navigation to see your saved content and resources.'
  },
  {
    q: 'How do I sign out?',
    a: 'Use the Logout button in the Navbar. It clears your token and returns you to the login page.'
  }
];

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hi! I\'m your study guide assistant. Ask me anything about navigating the app.' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // Floating action button position (draggable)
  const [fabPos, setFabPos] = useState(() => {
    try {
      const saved = localStorage.getItem('chatbot_fab_pos');
      return saved ? JSON.parse(saved) : { x: 24, y: 24 };
    } catch {
      return { x: 24, y: 24 };
    }
  });

  const fabRef = useRef(null);
  const draggingRef = useRef(false);
  const offsetRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    localStorage.setItem('chatbot_fab_pos', JSON.stringify(fabPos));
  }, [fabPos]);

  const startDrag = useCallback((e) => {
    draggingRef.current = true;
    const pointer = 'touches' in e ? e.touches[0] : e;
    const rect = fabRef.current?.getBoundingClientRect();
    offsetRef.current = {
      x: pointer.clientX - (rect?.left || 0),
      y: pointer.clientY - (rect?.top || 0)
    };
    e.preventDefault();
  }, []);

  const onDrag = useCallback((e) => {
    if (!draggingRef.current) return;
    const pointer = 'touches' in e ? e.touches[0] : e;
    const x = Math.max(8, Math.min(window.innerWidth - 64, pointer.clientX - offsetRef.current.x));
    const y = Math.max(8, Math.min(window.innerHeight - 64, pointer.clientY - offsetRef.current.y));
    setFabPos({ x, y });
  }, []);

  const endDrag = useCallback(() => {
    draggingRef.current = false;
  }, []);

  useEffect(() => {
    const handleMove = (e) => onDrag(e);
    const handleUp = () => endDrag();
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      window.removeEventListener('touchmove', handleMove);
      window.removeEventListener('touchend', handleUp);
    };
  }, [onDrag, endDrag]);

  const ask = useCallback((text) => {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setIsTyping(true);

    // Simulate answer lookup
    const answer = SAMPLE_QA.find((p) => text.toLowerCase().includes(p.q.toLowerCase().split('?')[0]))?.a
      || "I couldn't find an exact answer. Try asking about navigation, tools, vault, or logout.";

    setTimeout(() => {
      setMessages((prev) => [...prev, { role: 'bot', text: answer }]);
      setIsTyping(false);
    }, 650);
  }, []);

  const suggestions = useMemo(() => SAMPLE_QA.map((p) => p.q), []);

  const onSubmit = useCallback((e) => {
    e.preventDefault();
    ask(input);
  }, [ask, input]);

  return (
    <div className="chatbot-container" aria-live="polite">
      <div className="chatbot-drag-layer" />

      {/* Floating Action Button */}
      <div
        ref={fabRef}
        className="chatbot-fab"
        onMouseDown={startDrag}
        onTouchStart={startDrag}
        onClick={() => !draggingRef.current && setIsOpen((v) => !v)}
        style={{ right: `${fabPos.x}px`, bottom: `${fabPos.y}px`, position: 'fixed' }}
        aria-label={isOpen ? 'Close chatbot' : 'Open chatbot'}
        title={isOpen ? 'Close' : 'Chat with assistant'}
      >
        💬
        <div className="chatbot-grab-hint">drag me</div>
      </div>

      {isOpen && (
        <div className="chatbot-panel" role="dialog" aria-modal="true">
          <div className="chatbot-header">
            <div className="chatbot-title">
              <span>Assistant</span>
            </div>
            <button className="chatbot-close-btn" onClick={() => setIsOpen(false)} aria-label="Close">
              ✕
            </button>
          </div>

          <div className="chatbot-body">
            <div className="chatbot-suggestions">
              {suggestions.map((s, i) => (
                <button key={i} className="chatbot-chip" onClick={() => ask(s)}>{s}</button>
              ))}
            </div>

            <div className="chatbot-messages">
              {messages.map((m, idx) => (
                <div key={idx} className={`chatbot-message ${m.role}`}>{m.text}</div>
              ))}
              {isTyping && (
                <div className="chatbot-message bot">
                  <span className="chatbot-typing">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              )}
            </div>
          </div>

          <form className="chatbot-input" onSubmit={onSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the app..."
              aria-label="Ask the assistant"
            />
            <button type="submit" className="chatbot-send-btn">Send</button>
          </form>
        </div>
      )}
    </div>
  );
}

