"use client";

import { useEffect, useRef, useState } from "react";
import { sendChatMessage, ChatMessage } from "./chatActions";

function ChatBubbleIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M21 11.5c0 4.694-4.03 8.5-9 8.5-1.216 0-2.376-.224-3.434-.629L3 21l1.29-3.87C3.47 15.868 3 14.735 3 13.5 3 8.806 7.03 5 12 5s9 3.806 9 6.5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 20l16-8L4 4v6l10 2-10 2v6z" fill="currentColor" />
    </svg>
  );
}

const SUGGESTIONS = [
  "¿Cómo filtro por mi tarjeta?",
  "¿Qué significa 'vía tercero'?",
  "¿Qué tiendas tienen?",
];

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function handleSend(text?: string) {
    const content = (text ?? input).trim();
    if (!content || sending) return;

    setError(null);
    setInput("");
    const nextHistory = [...messages, { role: "user" as const, text: content }];
    setMessages(nextHistory);
    setSending(true);

    const result = await sendChatMessage(messages, content);
    setSending(false);

    if ("error" in result) {
      setError(result.error);
      return;
    }
    setMessages([...nextHistory, { role: "model", text: result.reply }]);
  }

  return (
    <div style={{ position: "fixed", right: 20, bottom: 20, zIndex: 50 }}>
      {open && (
        <div
          style={{
            width: 340,
            height: 460,
            marginBottom: 12,
            display: "flex",
            flexDirection: "column",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--color-border-strong)",
            background: "var(--color-surface)",
            boxShadow: "var(--shadow-card-hover)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "var(--color-accent)",
              color: "#fff",
            }}
          >
            <div>
              <p style={{ margin: 0, fontSize: 13.5, fontWeight: 700 }}>Asistente Quanto</p>
              <p style={{ margin: 0, fontSize: 11, opacity: 0.85 }}>Preguntame cómo funciona el sitio</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Cerrar chat"
              style={{
                border: "none",
                background: "transparent",
                color: "#fff",
                cursor: "pointer",
                display: "flex",
                padding: 4,
              }}
            >
              <CloseIcon />
            </button>
          </div>

          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 14,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {messages.length === 0 && (
              <div>
                <p style={{ fontSize: 12.5, color: "var(--color-text-muted)", margin: "0 0 10px" }}>
                  Puedo explicarte cómo buscar, cómo usar los filtros de categoría, tienda y tarjeta, o qué
                  significan los avisos que aparecen en los productos.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleSend(s)}
                      style={{
                        textAlign: "left",
                        fontSize: 12.5,
                        padding: "8px 10px",
                        borderRadius: 8,
                        border: "1px solid var(--color-border)",
                        background: "var(--color-bg)",
                        color: "var(--color-text)",
                        cursor: "pointer",
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                  padding: "9px 12px",
                  borderRadius: 12,
                  fontSize: 13,
                  lineHeight: 1.4,
                  background: m.role === "user" ? "var(--color-accent)" : "var(--color-bg)",
                  color: m.role === "user" ? "#fff" : "var(--color-text)",
                  border: m.role === "model" ? "1px solid var(--color-border)" : "none",
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.text}
              </div>
            ))}

            {sending && (
              <div
                style={{
                  alignSelf: "flex-start",
                  padding: "9px 12px",
                  borderRadius: 12,
                  fontSize: 13,
                  color: "var(--color-text-muted)",
                  border: "1px solid var(--color-border)",
                }}
              >
                Escribiendo…
              </div>
            )}

            {error && (
              <div style={{ fontSize: 12, color: "var(--color-accent)", padding: "0 2px" }}>{error}</div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              gap: 8,
              padding: 10,
              borderTop: "1px solid var(--color-border)",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              placeholder="Escribí tu pregunta..."
              style={{
                flex: 1,
                padding: "9px 12px",
                fontSize: 13,
                borderRadius: 999,
                border: "1px solid var(--color-border-strong)",
                outline: "none",
                background: "var(--color-bg)",
                color: "var(--color-text)",
              }}
            />
            <button
              type="button"
              onClick={() => handleSend()}
              disabled={sending || !input.trim()}
              aria-label="Enviar"
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                border: "none",
                background: "var(--color-accent)",
                color: "#fff",
                cursor: sending || !input.trim() ? "default" : "pointer",
                opacity: sending || !input.trim() ? 0.5 : 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <SendIcon />
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Cerrar chat" : "Abrir chat de ayuda"}
        style={{
          width: 54,
          height: 54,
          borderRadius: "50%",
          border: "none",
          background: "var(--color-accent)",
          color: "#fff",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "var(--shadow-card-hover)",
          marginLeft: "auto",
        }}
      >
        {open ? <CloseIcon /> : <ChatBubbleIcon />}
      </button>
    </div>
  );
}
