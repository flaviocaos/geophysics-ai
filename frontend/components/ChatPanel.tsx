"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  toolCalls?: Array<{ tool: string; input: Record<string, unknown> }>;
}

interface ChatPanelProps {
  surveyId: string;
}

export default function ChatPanel({ surveyId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      role: "assistant",
      content:
        "Pergunte, por exemplo: “qual a anomalia Bouguer da estação G005?” ou “interprete a refração sísmica da LINHA-01”. Todo número que eu reportar vem de uma ferramenta determinística — eu nunca calculo de cabeça.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    try {
      const res = await api.sendChatMessage(surveyId, text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, toolCalls: res.tool_calls }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Não consegui completar a análise (${String(err)}). Verifique se há estações/sondagens/linhas suficientes e se ANTHROPIC_API_KEY está configurada no backend.`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem", display: "flex", flexDirection: "column", gap: ".7rem" }}>
        {messages.map((m, i) => (
          <div key={i}>
            <div
              style={{
                background: m.role === "user" ? "var(--accent)" : "var(--surface-2)",
                color: m.role === "user" ? "#fff" : "var(--ink)",
                padding: ".6rem .85rem",
                borderRadius: 8,
                fontSize: ".9rem",
                maxWidth: "90%",
                marginLeft: m.role === "user" ? "auto" : 0,
                whiteSpace: "pre-wrap",
              }}
            >
              {m.content}
            </div>
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div style={{ fontSize: ".72rem", color: "var(--ink-muted)", marginTop: ".3rem", fontFamily: "monospace" }}>
                ferramentas chamadas: {m.toolCalls.map((t) => t.tool).join(", ")}
              </div>
            )}
          </div>
        ))}
        {sending && <p style={{ color: "var(--ink-muted)", fontSize: ".85rem" }}>Orquestrando análise…</p>}
      </div>

      <div style={{ display: "flex", gap: ".5rem", padding: ".8rem", borderTop: "1px solid var(--border)" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Pergunte ao agente…"
          style={{
            flex: 1,
            padding: ".6rem .8rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--ink)",
          }}
        />
        <button
          onClick={send}
          disabled={sending}
          style={{ padding: ".6rem 1rem", background: "var(--accent)", border: "none", borderRadius: 6, color: "#fff", fontWeight: 600 }}
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
