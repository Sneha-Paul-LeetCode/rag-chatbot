import { useEffect, useRef, useState, type ReactNode } from "react";

type Message = { role: "user" | "bot"; text: string; error?: boolean };

const LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;

// Turns [title](url) into real, clickable links; everything else stays plain text
function Linkified({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(LINK)) {
    const i = m.index ?? 0;
    if (i > last) parts.push(text.slice(last, i));
    parts.push(
      <a key={i} href={m[2]} target="_blank" rel="noopener noreferrer">
        {m[1]}
      </a>,
    );
    last = i + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

const STARTERS = [
  "What is the difference between a process and a thread?",
  "How does a load balancer work?",
  "When does a composite index help in SQL?",
  "What are the main techniques for solving array problems?",
  "Give me the top 10 Adobe questions from the last 6 months",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || loading) return;

    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Request failed. Please try again.");
      }
      const data: { answer: string } = await res.json();
      setMessages((m) => [...m, { role: "bot", text: data.answer }]);
    } catch (e) {
      const text =
        e instanceof TypeError
          ? "Can't reach the server. Start the API with: uvicorn api:app --reload"
          : e instanceof Error
            ? e.message
            : "Something went wrong.";
      setMessages((m) => [...m, { role: "bot", text, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="top">
        <span className="brand">Interview Notes</span>
        {messages.length > 0 && (
          <button className="ghost" onClick={() => setMessages([])} disabled={loading}>
            New chat
          </button>
        )}
      </header>

      <main className="thread" aria-live="polite">
        <div className="inner">
          {messages.length === 0 ? (
            <section className="empty">
              <h1>What do you want to revise?</h1>
              <p>Ask about operating systems, networking, databases, system design or algorithms.</p>
              <ul className="starters">
                {STARTERS.map((q) => (
                  <li key={q}>
                    <button onClick={() => send(q)}>{q}</button>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}${m.error ? " error" : ""}`}>
                {m.role === "bot" && !m.error ? <Linkified text={m.text} /> : m.text}
              </div>
            ))
          )}
          {loading && (
            <div className="msg bot" aria-label="Thinking">
              <span className="dots"><i /><i /><i /></span>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </main>

      <footer className="composer">
        <form
          className="inner"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask a question"
            aria-label="Your question"
            rows={1}
            maxLength={500}
          />
          <button type="submit" className="send" disabled={loading || !input.trim()}>
            Ask
          </button>
        </form>
      </footer>
    </div>
  );
}
