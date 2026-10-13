"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, GeophysicalSurvey } from "@/lib/api";

export default function SurveysPage() {
  const [surveys, setSurveys] = useState<GeophysicalSurvey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listSurveys()
      .then(setSurveys)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <p style={{ fontFamily: "monospace", fontSize: ".75rem", letterSpacing: ".08em", color: "var(--ink-muted)" }}>
        GEOPHYSICS AI
      </p>
      <h1 style={{ fontSize: "1.8rem", marginTop: ".3rem" }}>Levantamentos geofísicos</h1>
      <p style={{ color: "var(--ink-muted)", fontSize: ".9rem", marginTop: ".2rem" }}>
        Redução gravimétrica (Bouguer), redução ao polo magnética, sondagem elétrica vertical e
        refração sísmica — sempre a partir de funções determinísticas, nunca calculadas pelo LLM.
      </p>

      {loading && <p style={{ color: "var(--ink-muted)" }}>Carregando…</p>}
      {error && <p style={{ color: "var(--bad)" }}>Não foi possível carregar os levantamentos ({error}).</p>}

      <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: ".6rem", marginTop: "1.5rem" }}>
        {surveys.map((s) => (
          <li key={s.id}>
            <Link
              href={`/surveys/${s.id}`}
              style={{
                display: "block",
                padding: "1rem 1.2rem",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                textDecoration: "none",
                color: "var(--ink)",
              }}
            >
              <strong>{s.name}</strong>
              <p style={{ margin: ".3rem 0 0", color: "var(--ink-muted)", fontSize: ".9rem" }}>
                tipo: {s.survey_type}
                {" · criado em "}
                {new Date(s.created_at).toLocaleDateString("pt-BR")}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      {!loading && !error && surveys.length === 0 && (
        <p style={{ color: "var(--ink-muted)", marginTop: "1.5rem" }}>
          Nenhum levantamento cadastrado ainda — rode <code>python -m scripts.seed_demo_data</code> no
          backend para gerar um levantamento de demonstração.
        </p>
      )}
    </main>
  );
}
