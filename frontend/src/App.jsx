import { useEffect, useRef, useState } from "react";

const AUTO = "auto";

const AUTO_WELCOME =
  "Hi! Ask me about any of the products on the left and I'll send your question to the right assistant.";

// One id per page load, so the server keeps follow-up questions with the same product.
const THREAD_ID =
  globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const AGENT_LABELS = {
  router: "Router",
  clarify: "Clarify",
  general_agent: "General knowledge",
  escalate: "Escalation",
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
  const [products, setProducts] = useState([]);
  const [selected, setSelected] = useState(AUTO);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    fetch("/api/products")
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`status ${res.status}`))))
      .then(setProducts)
      .catch((err) => setLoadError(`Couldn't load the product list (${err.message}). Is the API running?`));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const product = products.find((p) => p.id === selected);
  const welcome = product ? product.welcome : AUTO_WELCOME;
  const suggestions = product
    ? product.suggestions
    : products.map((p) => p.suggestions[0]).filter(Boolean);

  // "phone_agent" -> "Zentro A5 agent"
  function agentLabel(agent) {
    if (AGENT_LABELS[agent]) return AGENT_LABELS[agent];
    const p = products.find((x) => `${x.id}_agent` === agent);
    return p ? `${p.name} agent` : agent;
  }

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
        body: JSON.stringify({
          question,
          product_id: selected === AUTO ? null : selected,
          thread_id: THREAD_ID,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: data.answer,
          citations: data.citations,
          escalated: !data.found,
          general: data.source === "general",
          productName: data.product_name,
          trace: data.trace,
        },
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
        <nav className="picker" aria-label="Choose a product">
          <button
            className={selected === AUTO ? "active" : ""}
            aria-pressed={selected === AUTO}
            onClick={() => setSelected(AUTO)}
          >
            Auto
          </button>
          {products.map((p) => (
            <button
              key={p.id}
              className={selected === p.id ? "active" : ""}
              aria-pressed={selected === p.id}
              onClick={() => setSelected(p.id)}
            >
              {p.name}
            </button>
          ))}
        </nav>

        {loadError && <p className="load-error">{loadError}</p>}

        {product ? (
          <>
            <p className="brand">{product.brand}</p>
            <h1>{product.name}</h1>
            <p className="tagline">{product.tagline}</p>

            <dl className="specs">
              {product.specs.map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>

            {product.general_fallback && (
              <p className="note">
                If the documents don't cover a question, this assistant gives general
                information and labels it clearly.
              </p>
            )}

            {product.contact_text && (
              <p className="contact">
                {product.contact_label} <a href={product.contact_href}>{product.contact_text}</a>
              </p>
            )}
          </>
        ) : (
          <>
            <p className="brand">Multi-agent support</p>
            <h1>All products</h1>
            <p className="tagline">
              A router agent reads your question and passes it to the assistant for the right
              product. Pick a product above to talk to one assistant only.
            </p>

            <ul className="product-list">
              {products.map((p) => (
                <li key={p.id}>
                  <button onClick={() => setSelected(p.id)}>
                    <strong>{p.name}</strong>
                    <span>{p.tagline}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </aside>

      <main className="chat">
        <header className="chat-header">
          <span className="dot" aria-hidden="true" />
          {product ? `${product.name} assistant` : "Support assistant"}
        </header>

        <div className="messages" aria-live="polite">
          <div className="msg bot">
            <p>{welcome}</p>
          </div>

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`msg ${msg.role}${msg.error ? " error" : ""}${msg.escalated ? " escalated" : ""}${msg.general ? " general" : ""}`}
            >
              {msg.role === "bot" && msg.productName && (
                <p className="answered-by">
                  {msg.productName}
                  {msg.general && <span className="badge">General information</span>}
                </p>
              )}
              <p>{msg.text}</p>
              {msg.citations?.length > 0 && (
                <ul className="sources">
                  {msg.citations.map((c) => (
                    <li key={c}>{formatCitation(c)}</li>
                  ))}
                </ul>
              )}
              {msg.trace?.length > 0 && (
                <details className="trace">
                  <summary>{msg.trace.map((s) => agentLabel(s.agent)).join(" → ")}</summary>
                  <ol>
                    {msg.trace.map((s, j) => (
                      <li key={j}>
                        <strong>{agentLabel(s.agent)}:</strong> {s.detail}
                      </li>
                    ))}
                  </ol>
                </details>
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

        {messages.length === 0 && suggestions.length > 0 && (
          <div className="suggestions">
            {suggestions.map((s) => (
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
            placeholder={product ? `Ask about ${product.name}…` : "Ask about any product…"}
            aria-label="Your question"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>Send</button>
        </form>
      </main>
    </div>
  );
}
