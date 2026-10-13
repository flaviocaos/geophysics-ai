"use client";

import { useState } from "react";
import { BouguerAnomalyResult, GravityStation, api } from "@/lib/api";
import XYChart from "@/components/XYChart";

interface GravityPanelProps {
  stations: GravityStation[];
}

export default function GravityPanel({ stations }: GravityPanelProps) {
  const [density, setDensity] = useState(2670);
  const [results, setResults] = useState<Record<string, BouguerAnomalyResult>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runProfile = async () => {
    if (stations.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const entries = await Promise.all(
        stations.map(async (s) => [s.id, await api.calculateBouguerAnomaly(s.id, density)] as const)
      );
      setResults(Object.fromEntries(entries));
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const profilePoints = stations
    .map((s, i) => {
      const r = results[s.id];
      return r ? { x: i, y: r.bouguer_anomaly_mgal } : null;
    })
    .filter((p): p is { x: number; y: number } => p !== null);

  const anyResult = Object.values(results)[0];

  return (
    <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <section>
        <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>
          Redução Bouguer — perfil de {stations.length} estação(ões)
        </h3>
        <div style={{ display: "flex", gap: ".5rem", alignItems: "center", marginBottom: ".6rem" }}>
          <label style={{ fontSize: ".75rem", color: "var(--ink-muted)" }}>densidade (kg/m³)</label>
          <input
            type="number"
            value={density}
            onChange={(e) => setDensity(Number(e.target.value))}
            style={{ width: 90, padding: ".35rem .5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)" }}
          />
          <button
            onClick={runProfile}
            disabled={loading || stations.length === 0}
            style={{ padding: ".5rem 1rem", background: "var(--accent)", border: "none", borderRadius: 6, color: "#fff", fontSize: ".8rem", fontWeight: 600 }}
          >
            {loading ? "Calculando…" : "Calcular perfil"}
          </button>
        </div>
        {error && <p style={{ fontSize: ".8rem", color: "var(--bad)" }}>{error}</p>}
        {stations.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma estação gravimétrica cadastrada.</p>}

        {profilePoints.length > 0 && (
          <>
            <XYChart
              series={[{ points: profilePoints, color: "var(--accent)", mode: "line" }]}
              xLabel="estação (índice do perfil)"
              yLabel="anomalia Bouguer (mGal)"
            />
            <div style={{ overflowX: "auto", marginTop: ".6rem" }}>
              <table>
                <thead>
                  <tr>
                    <th>código</th>
                    <th>elevação (m)</th>
                    <th>g teórico (mGal)</th>
                    <th>FAC (mGal)</th>
                    <th>BC (mGal)</th>
                    <th>anomalia Bouguer (mGal)</th>
                  </tr>
                </thead>
                <tbody>
                  {stations.map((s) => {
                    const r = results[s.id];
                    if (!r) return null;
                    return (
                      <tr key={s.id}>
                        <td>{s.code}</td>
                        <td>{s.elevation_m.toFixed(1)}</td>
                        <td>{r.normal_gravity_mgal.toFixed(2)}</td>
                        <td>{r.free_air_correction_mgal.toFixed(3)}</td>
                        <td>{r.bouguer_correction_mgal.toFixed(3)}</td>
                        <td>
                          <strong>{r.bouguer_anomaly_mgal.toFixed(3)}</strong>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {anyResult && <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", marginTop: ".6rem", lineHeight: 1.5 }}>{anyResult.limitations}</p>}
          </>
        )}
      </section>
    </div>
  );
}
