"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { SeismicLine, SeismicReading, SeismicRefractionResult, api } from "@/lib/api";
import XYChart, { ChartSeries } from "@/components/XYChart";

interface SeismicPanelProps {
  surveyId: string;
  lines: SeismicLine[];
  onChanged: () => void;
}

export default function SeismicPanel({ surveyId, lines, onChanged }: SeismicPanelProps) {
  const [selectedId, setSelectedId] = useState(lines[0]?.id ?? "");
  const [readings, setReadings] = useState<SeismicReading[]>([]);
  const [result, setResult] = useState<SeismicRefractionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [code, setCode] = useState("");
  const [coordsText, setCoordsText] = useState("-47.9010,-15.7800\n-47.8990,-15.7800");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const addLine = async () => {
    const coordinates = coordsText
      .split("\n")
      .map((row) => row.trim())
      .filter((row) => row.length > 0)
      .map((row) => row.split(",").map((v) => Number(v.trim())));

    const valid = coordinates.length >= 2 && coordinates.every((pt) => pt.length === 2 && pt.every((v) => !Number.isNaN(v)));
    if (!code.trim() || !valid) {
      setSaveError("Informe um código e ao menos 2 pontos válidos, um por linha, no formato longitude,latitude.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const created = await api.createSeismicLine(surveyId, { code: code.trim(), coordinates });
      setCode("");
      setShowAddForm(false);
      setSelectedId(created.id);
      onChanged();
    } catch (err) {
      setSaveError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleImportFile = async (file: File) => {
    if (!selectedId) return;
    setImporting(true);
    setImportError(null);
    setImportMsg(null);
    try {
      const res = await api.importSeismicReadingsCsv(selectedId, file);
      setImportMsg(`${res.n_readings_created} leitura(s) importada(s) com sucesso.`);
      api.listSeismicReadings(selectedId).then(setReadings).catch(() => {});
      onChanged();
    } catch (err) {
      setImportError(String(err));
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>
            Refração sísmica (2 camadas) — {lines.length} linha(s)
          </h3>
          <button onClick={() => setShowAddForm((v) => !v)} style={linkBtn}>
            {showAddForm ? "cancelar" : "+ nova linha"}
          </button>
        </div>

        {showAddForm && (
          <div style={addBox}>
            <input placeholder="código (ex.: LINHA-02)" value={code} onChange={(e) => setCode(e.target.value)} style={{ ...numStyle, width: "100%" }} />
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: ".6rem 0 .3rem" }}>
              Pontos da linha (um por linha, longitude,latitude — pelo menos 2: início e fim):
            </p>
            <textarea
              value={coordsText}
              onChange={(e) => setCoordsText(e.target.value)}
              rows={4}
              style={{ width: "100%", padding: ".5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)", fontFamily: "monospace", fontSize: ".78rem" }}
            />
            {saveError && <p style={{ fontSize: ".78rem", color: "var(--bad)", margin: ".4rem 0 0" }}>{saveError}</p>}
            <button onClick={addLine} disabled={saving} style={{ ...btnStyle, marginTop: ".5rem" }}>
              {saving ? "Salvando…" : "Salvar linha"}
            </button>
          </div>
        )}

        <div style={{ display: "flex", gap: ".5rem", margin: "1rem 0 .6rem" }}>
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
          <button onClick={run} disabled={!selectedId || loading} style={btnStyle}>
            {loading ? "Interpretando…" : "Interpretar"}
          </button>
        </div>
        {lines.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma linha sísmica cadastrada ainda.</p>}

        {selectedId && (
          <div style={{ ...addBox, marginBottom: "1rem" }}>
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: "0 0 .4rem" }}>
              Importar leituras de primeira chegada da linha selecionada (CSV: offset_m,first_arrival_time_ms,is_direct_wave[opcional])
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={(e) => e.target.files && e.target.files[0] && handleImportFile(e.target.files[0])}
              disabled={importing}
              style={{ fontSize: ".78rem", color: "var(--ink-muted)" }}
            />
            {importing && <p style={{ fontSize: ".76rem", color: "var(--ink-muted)", margin: ".3rem 0 0" }}>Importando…</p>}
            {importMsg && <p style={{ fontSize: ".76rem", color: "var(--good, #4f9c7c)", margin: ".3rem 0 0" }}>{importMsg}</p>}
            {importError && <p style={{ fontSize: ".76rem", color: "var(--bad)", margin: ".3rem 0 0" }}>{importError}</p>}
          </div>
        )}

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

const numStyle: CSSProperties = {
  padding: ".35rem .5rem",
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--ink)",
};

const btnStyle: CSSProperties = {
  padding: ".5rem 1rem",
  background: "var(--accent)",
  border: "none",
  borderRadius: 6,
  color: "#fff",
  fontSize: ".8rem",
  fontWeight: 600,
};

const linkBtn: CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--accent)",
  fontSize: ".78rem",
  fontWeight: 600,
  cursor: "pointer",
  padding: 0,
};

const addBox: CSSProperties = {
  marginTop: ".6rem",
  padding: ".8rem",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
};
