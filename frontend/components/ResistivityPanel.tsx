"use client";

import { useState } from "react";
import { ResistivitySounding, ResistivitySoundingResult, api } from "@/lib/api";
import XYChart from "@/components/XYChart";

interface ResistivityPanelProps {
  soundings: ResistivitySounding[];
}

export default function ResistivityPanel({ soundings }: ResistivityPanelProps) {
  const [selectedId, setSelectedId] = useState(soundings[0]?.id ?? "");
  const [result, setResult] = useState<ResistivitySoundingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    api
      .calculateResistivitySounding(selectedId)
      .then(setResult)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  const curvePoints =
    result?.sounding_curve.map((p) => ({ x: p.estimated_investigation_depth_m * (result.array_type === "wenner" ? 2 : 4), y: p.apparent_resistivity_ohm_m })) ?? [];

  return (
    <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <section>
        <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>Sondagem elétrica vertical (SEV)</h3>
        <div style={{ display: "flex", gap: ".5rem", marginBottom: ".6rem" }}>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            style={{ flex: 1, padding: ".4rem .5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)" }}
          >
            {soundings.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} ({s.array_type})
              </option>
            ))}
          </select>
          <button
            onClick={run}
            disabled={!selectedId || loading}
            style={{ padding: ".5rem 1rem", background: "var(--accent)", border: "none", borderRadius: 6, color: "#fff", fontSize: ".8rem", fontWeight: 600 }}
          >
            {loading ? "Calculando…" : "Calcular curva"}
          </button>
        </div>
        {soundings.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma sondagem cadastrada.</p>}
        {error && <p style={{ fontSize: ".8rem", color: "var(--bad)" }}>{error}</p>}

        {result && (
          <>
            <XYChart
              series={[{ points: curvePoints, color: "var(--accent)", mode: "line" }]}
              xLabel="espaçamento (m)"
              yLabel="resistividade aparente (Ω·m)"
              logX
              logY
            />
            <div style={{ overflowX: "auto", marginTop: ".6rem" }}>
              <table>
                <thead>
                  <tr>
                    <th>espaçamento (m)</th>
                    <th>ρ aparente (Ω·m)</th>
                    <th>profundidade estimada (m)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.sounding_curve.map((p, i) => (
                    <tr key={i}>
                      <td>{(p.estimated_investigation_depth_m * (result.array_type === "wenner" ? 2 : 4)).toFixed(1)}</td>
                      <td>{p.apparent_resistivity_ohm_m.toFixed(1)}</td>
                      <td>{p.estimated_investigation_depth_m.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", marginTop: ".5rem", lineHeight: 1.5 }}>{result.limitations}</p>
          </>
        )}
      </section>
    </div>
  );
}
