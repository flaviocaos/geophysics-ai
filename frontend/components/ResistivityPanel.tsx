"use client";

import { useRef, useState } from "react";
import type { CSSProperties } from "react";
import { ResistivitySounding, ResistivitySoundingResult, api } from "@/lib/api";
import XYChart from "@/components/XYChart";

interface ResistivityPanelProps {
  surveyId: string;
  soundings: ResistivitySounding[];
  onChanged: () => void;
}

export default function ResistivityPanel({ surveyId, soundings, onChanged }: ResistivityPanelProps) {
  const [selectedId, setSelectedId] = useState(soundings[0]?.id ?? "");
  const [result, setResult] = useState<ResistivitySoundingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [code, setCode] = useState("");
  const [lon, setLon] = useState("");
  const [lat, setLat] = useState("");
  const [arrayType, setArrayType] = useState<"wenner" | "schlumberger">("wenner");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const addSounding = async () => {
    const lonNum = Number(lon);
    const latNum = Number(lat);
    if (!code.trim() || Number.isNaN(lonNum) || Number.isNaN(latNum)) {
      setSaveError("Preencha código, longitude e latitude com valores válidos.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const created = await api.createResistivitySounding(surveyId, { code: code.trim(), lon: lonNum, lat: latNum, array_type: arrayType });
      setCode("");
      setLon("");
      setLat("");
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
      const res = await api.importResistivityReadingsCsv(selectedId, file);
      setImportMsg(`${res.n_readings_created} leitura(s) importada(s) com sucesso. Clique em "Calcular curva" para ver o resultado.`);
      onChanged();
    } catch (err) {
      setImportError(String(err));
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const curvePoints =
    result?.sounding_curve.map((p) => ({ x: p.estimated_investigation_depth_m * (result.array_type === "wenner" ? 2 : 4), y: p.apparent_resistivity_ohm_m })) ?? [];

  return (
    <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>
            Sondagem elétrica vertical (SEV) — {soundings.length} cadastrada(s)
          </h3>
          <button onClick={() => setShowAddForm((v) => !v)} style={linkBtn}>
            {showAddForm ? "cancelar" : "+ nova sondagem"}
          </button>
        </div>

        {showAddForm && (
          <div style={addBox}>
            <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
              <input placeholder="código (ex.: SEV-02)" value={code} onChange={(e) => setCode(e.target.value)} style={{ ...numStyle, width: 120 }} />
              <input placeholder="longitude" type="number" value={lon} onChange={(e) => setLon(e.target.value)} style={numStyle} />
              <input placeholder="latitude" type="number" value={lat} onChange={(e) => setLat(e.target.value)} style={numStyle} />
              <select value={arrayType} onChange={(e) => setArrayType(e.target.value as "wenner" | "schlumberger")} style={numStyle}>
                <option value="wenner">Wenner</option>
                <option value="schlumberger">Schlumberger</option>
              </select>
            </div>
            {saveError && <p style={{ fontSize: ".78rem", color: "var(--bad)", margin: ".4rem 0 0" }}>{saveError}</p>}
            <button onClick={addSounding} disabled={saving} style={{ ...btnStyle, marginTop: ".5rem" }}>
              {saving ? "Salvando…" : "Salvar sondagem"}
            </button>
          </div>
        )}

        <div style={{ display: "flex", gap: ".5rem", margin: "1rem 0 .6rem" }}>
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
          <button onClick={run} disabled={!selectedId || loading} style={btnStyle}>
            {loading ? "Calculando…" : "Calcular curva"}
          </button>
        </div>
        {soundings.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma sondagem cadastrada ainda.</p>}

        {selectedId && (
          <div style={{ ...addBox, marginBottom: "1rem" }}>
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: "0 0 .4rem" }}>
              Importar leituras de campo da sondagem selecionada (CSV: voltage_v,current_ma,spacing_m — Wenner — ou
              voltage_v,current_ma,current_spacing_m,potential_spacing_m — Schlumberger)
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

const numStyle: CSSProperties = {
  width: 110,
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
