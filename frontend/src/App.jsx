import { useEffect, useRef, useState } from "react";

const AUTO = "auto";

const AUTO_WELCOME =
  "Hi! Ask me about any of the products on the left and I'll send your question to the right assistant.";

// One id per page load, so the server keeps follow-up questions with the same product.
const THREAD_ID =
  globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const AGENT_LABELS = {
  api: "API",
  router: "Router",
  clarify: "Clarify",
  general_agent: "General knowledge",
  escalate: "Escalation",
};

// Merge one progress event into the activity list. Each agent gets one row: "running"
// events update its text, and "done" marks it finished and records how long it took.
function applyProgress(steps, ev) {
  const now = performance.now();
  const last = steps[steps.length - 1];
  if (last && last.agent === ev.agent && last.status === "running") {
    const updated = { ...last, detail: ev.detail, status: ev.status };
    if (ev.status === "done") updated.ms = now - last.start;
    return [...steps.slice(0, -1), updated];
  }
  return [
    ...steps,
    { agent: ev.agent, detail: ev.detail, status: ev.status, start: now, ms: ev.status === "done" ? 0 : null },
  ];
}

function formatMs(ms) {
  if (ms == null || ms < 50) return "";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

const capitalize = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : t);

// Read a newline-delimited JSON stream, calling onEvent for every line.
async function readEvents(res, onEvent) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line));
    if (done) break;
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [selected, setSelected] = useState(AUTO);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activity, setActivity] = useState([]); // live steps for the question in flight
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
  }, [messages, loading, activity]);

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
    setActivity([]);
    const started = performance.now();
    let steps = [];
    let data = null;

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          product_id: selected === AUTO ? null : selected,
          thread_id: THREAD_ID,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed (${res.status})`);
      }
      await readEvents(res, (ev) => {
        if (ev.type === "progress") {
          steps = applyProgress(steps, ev);
          setActivity(steps);
        } else if (ev.type === "answer") {
          data = ev;
        } else if (ev.type === "error") {
          throw new Error(ev.detail);
        }
      });
      if (!data) throw new Error("The answer didn't arrive.");
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: data.answer,
          escalated: !data.found,
          general: data.source === "general",
          productName: data.product_name,
          activity: steps,
          totalMs: performance.now() - started,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "bot", error: true, text: `Couldn't reach the support bot. ${err.message}`, activity: steps },
      ]);
    } finally {
      setLoading(false);
      setActivity([]);
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
              {msg.activity?.length > 0 && (
                <details className="trace">
                  <summary>
                    {msg.activity
                      .filter((s) => s.agent !== "api")
                      .map((s) => agentLabel(s.agent))
                      .join(" → ")}
                    {msg.totalMs ? ` · ${formatMs(msg.totalMs)}` : ""}
                  </summary>
                  <ActivityList steps={msg.activity} agentLabel={agentLabel} />
                </details>
              )}
            </div>
          ))}
          {loading && (
            <div className="msg bot activity" aria-label="Working on your question">
              <p className="activity-title">Working on it…</p>
              <ActivityList steps={activity} agentLabel={agentLabel} live />
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

// The steps the agents took. While a question is in flight (`live`), the step that is
// still running shows a spinner and a "waiting for the server" row appears before the first event.
function ActivityList({ steps, agentLabel, live = false }) {
  return (
    <ol className="steps">
      {live && steps.length === 0 && (
        <li className="step running">
          <span className="step-icon" aria-hidden="true" />
          <span className="step-text">
            <strong>API</strong> Sending your question
          </span>
        </li>
      )}
      {steps.map((s, i) => (
        <li key={i} className={`step ${s.status}`}>
          <span className="step-icon" aria-hidden="true" />
          <span className="step-text">
            <strong>{agentLabel(s.agent)}</strong> {capitalize(s.detail)}
          </span>
          {s.status === "done" && <span className="step-time">{formatMs(s.ms)}</span>}
        </li>
      ))}
    </ol>
  );
}
