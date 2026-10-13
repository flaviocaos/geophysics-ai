"use client";

import { useEffect, useState } from "react";
import { SeismicLine, SeismicReading, SeismicRefractionResult, api } from "@/lib/api";
import XYChart, { ChartSeries } from "@/components/XYChart";

interface SeismicPanelProps {
  lines: SeismicLine[];
}

export default function SeismicPanel({ lines }: SeismicPanelProps) {
  const [selectedId, setSelectedId] = useState(lines[0]?.id ?? "");
  const [readings, setReadings] = useState<SeismicReading[]>([]);
  const [result, setResult] = useState<SeismicRefractionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    api.listSeismicReadings(selectedId).then(setReadings).catch(() => setReadings([]));
    setResult(null);
  }, [selectedId]);

  const run = () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    api
      .interpretSeismicRefraction(selectedId)
      .then(setResult)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  const direct = readings.filter((r) => r.is_direct_wave === true);
  const refracted = readings.filter((r) => r.is_direct_wave === false);

  const series: ChartSeries[] = [
    { points: direct.map((r) => ({ x: r.offset_m, y: r.first_arrival_time_ms })), color: "#3f7fd9", mode: "scatter" },
    { points: refracted.map((r) => ({ x: r.offset_m, y: r.first_arrival_time_ms })), color: "#d9a441", mode: "scatter" },
  ];

  if (result) {
    const maxOffset = Math.max(...readings.map((r) => r.offset_m), result.crossover_distance_m * 3);
    series.push({
      points: [
        { x: 0, y: 0 },
        { x: result.crossover_distance_m, y: (result.crossover_distance_m / result.v1_m_s) * 1000 },
      ],
      color: "#4f9c7c",
      mode: "line",
    });
    series.push({
      points: [
        { x: result.crossover_distance_m, y: (result.crossover_distance_m / result.v1_m_s) * 1000 },
        { x: maxOffset, y: (maxOffset / result.v2_m_s) * 1000 + result.intercept_time_s * 1000 },
      ],
      color: "#d1594f",
      mode: "line",
    });
  }

  return (
    <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <section>
        <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>Refração sísmica (2 camadas)</h3>
        <div style={{ display: "flex", gap: ".5rem", marginBottom: ".6rem" }}>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            style={{ flex: 1, padding: ".4rem .5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)" }}
          >
            {lines.map((l) => (
              <option key={l.id} value={l.id}>
                {l.code}
              </option>
            ))}
          </select>
          <button
            onClick={run}
            disabled={!selectedId || loading}
            style={{ padding: ".5rem 1rem", background: "var(--accent)", border: "none", borderRadius: 6, color: "#fff", fontSize: ".8rem", fontWeight: 600 }}
          >
            {loading ? "Interpretando…" : "Interpretar"}
          </button>
        </div>
        {lines.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma linha sísmica cadastrada.</p>}
        {error && <p style={{ fontSize: ".8rem", color: "var(--bad)" }}>{error}</p>}

        {readings.length > 0 && <XYChart series={series} xLabel="offset (m)" yLabel="tempo (ms)" />}

        {result && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: ".4rem", marginTop: ".8rem", fontSize: ".76rem" }}>
              <Tile label="V1 (m/s)" value={result.v1_m_s.toFixed(0)} />
              <Tile label="V2 (m/s)" value={result.v2_m_s.toFixed(0)} />
              <Tile label="ângulo crítico (°)" value={result.critical_angle_deg.toFixed(2)} />
              <Tile label="x cruzamento (m)" value={result.crossover_distance_m.toFixed(1)} />
              <Tile label="profundidade (m)" value={result.depth_m.toFixed(2)} />
              <Tile label="prof. (t intercepto) (m)" value={result.depth_from_intercept_time_m.toFixed(2)} />
            </div>
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", marginTop: ".6rem", lineHeight: 1.5 }}>{result.limitations}</p>
          </>
        )}
      </section>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: ".5rem .6rem" }}>
      <div style={{ fontSize: ".65rem", color: "var(--ink-muted)" }}>{label}</div>
      <div style={{ fontSize: ".85rem", fontWeight: 600, marginTop: ".1rem" }}>{value}</div>
    </div>
  );
}
