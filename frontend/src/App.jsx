import { useEffect, useRef, useState } from "react";

const SPECS = [
  ["Capacity", "1.5 L (min 0.5 L)"],
  ["Power", "1500 W · 120 V"],
  ["Presets", "70° · 80° · 90° · 100°C"],
  ["Keep-warm", "Up to 60 min"],
  ["Connectivity", "2.4 GHz Wi-Fi"],
  ["Warranty", "2-year limited"],
];

const SUGGESTIONS = [
  "How do I descale the kettle?",
  "My kettle shows E1",
  "The app can't find my kettle",
  "How long is the warranty?",
];

const WELCOME = {
  role: "bot",
  text: "Hi! I can answer questions about the Kettlewise K2 using the official docs. What do you need help with?",
};

// "user_manual.md#Descaling" -> "User Manual › Descaling"
function formatCitation(id) {
  const [file, section] = id.split("#");
  const doc = file
    .replace(/\.md$/, "")
    .split("_")
    .map((w) => (w === "and" ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(" ");
  return section ? `${doc} › ${section}` : doc;
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const question = text.trim();
    if (!question || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      setMessages((m) => [
        ...m,
        { role: "bot", text: data.answer, citations: data.citations, escalated: !data.found },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "bot", error: true, text: `Couldn't reach the support bot. ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <aside className="product">
        <p className="brand">RAG Appliances</p>
        <h1>Kettlewise K2</h1>
        <p className="tagline">Smart kettle with precise temperature control and app scheduling.</p>

        <dl className="specs">
          {SPECS.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>

        <p className="contact">
          Need a person? <a href="mailto:support@rag.example">support@rag.example</a>
        </p>
      </aside>

      <main className="chat">
        <header className="chat-header">
          <span className="dot" aria-hidden="true" />
          Support assistant
        </header>

        <div className="messages" aria-live="polite">
          {messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role}${msg.error ? " error" : ""}${msg.escalated ? " escalated" : ""}`}>
              <p>{msg.text}</p>
              {msg.citations?.length > 0 && (
                <ul className="sources">
                  {msg.citations.map((c) => (
                    <li key={c}>{formatCitation(c)}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {loading && (
            <div className="msg bot typing" aria-label="Assistant is typing">
              <span /><span /><span />
            </div>
          )}
          <div ref={endRef} />
        </div>

        {messages.length === 1 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your Kettlewise K2…"
            aria-label="Your question"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>Send</button>
        </form>
      </main>
    </div>
  );
}
