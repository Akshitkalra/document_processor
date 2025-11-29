import React, { useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { chat } from "../api.js";

export default function ChatPanel({ document }) {
  const [messages, setMessages] = useState([]); // {role, content, citations?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  // Reset the conversation when switching documents.
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [document.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError(null);

    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setBusy(true);
    try {
      const res = await chat(document.id, question, history);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.answer, citations: res.citations },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel chat">
      <div className="chat-log">
        {messages.length === 0 && (
          <p className="muted">
            Ask anything about “{document.filename}”. Answers cite page numbers.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <ReactMarkdown>{m.content}</ReactMarkdown>
            {m.citations?.length > 0 && (
              <details className="citations">
                <summary>{m.citations.length} sources</summary>
                {m.citations.map((c) => (
                  <div key={c.chunk_id} className="citation">
                    <span className="cite-page">
                      {c.page != null ? `p. ${c.page}` : "—"} ·{" "}
                      {(c.score * 100).toFixed(0)}%
                    </span>
                    <span className="cite-text">{c.text}</span>
                  </div>
                ))}
              </details>
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant thinking">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="error">{error}</div>}

      <div className="chat-input">
        <textarea
          rows={2}
          value={input}
          placeholder="Ask a question…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
