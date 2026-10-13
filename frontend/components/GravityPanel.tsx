"use client";

import { useRef, useState } from "react";
import type { CSSProperties } from "react";
import { BouguerAnomalyResult, GravityStation, api } from "@/lib/api";
import XYChart from "@/components/XYChart";

interface GravityPanelProps {
  surveyId: string;
  stations: GravityStation[];
  onChanged: () => void;
}

export default function GravityPanel({ surveyId, stations, onChanged }: GravityPanelProps) {
  const [density, setDensity] = useState(2670);
  const [results, setResults] = useState<Record<string, BouguerAnomalyResult>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [code, setCode] = useState("");
  const [lon, setLon] = useState("");
  const [lat, setLat] = useState("");
  const [elevation, setElevation] = useState("");
  const [observedGravity, setObservedGravity] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const addStation = async () => {
    const lonNum = Number(lon);
    const latNum = Number(lat);
    const elevNum = Number(elevation);
    const gravNum = Number(observedGravity);
    if (!code.trim() || [lonNum, latNum, elevNum, gravNum].some((v) => Number.isNaN(v))) {
      setSaveError("Preencha código, longitude, latitude, elevação e gravidade observada com valores válidos.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await api.createGravityStation(surveyId, {
        code: code.trim(),
        lon: lonNum,
        lat: latNum,
        latitude_deg: latNum,
        elevation_m: elevNum,
        observed_gravity_mgal: gravNum,
      });
      setCode("");
      setLon("");
      setLat("");
      setElevation("");
      setObservedGravity("");
      setShowAddForm(false);
      onChanged();
    } catch (err) {
      setSaveError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleImportFile = async (file: File) => {
    setImporting(true);
    setImportError(null);
    setImportMsg(null);
    try {
      const res = await api.importGravityStationsCsv(surveyId, file);
      setImportMsg(`${res.n_stations_created} estação(ões) importada(s) com sucesso.`);
      onChanged();
    } catch (err) {
      setImportError(String(err));
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>
            Estações gravimétricas ({stations.length})
          </h3>
          <button onClick={() => setShowAddForm((v) => !v)} style={linkBtn}>
            {showAddForm ? "cancelar" : "+ adicionar estação"}
          </button>
        </div>

        {showAddForm && (
          <div style={addBox}>
            <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
              <input placeholder="código (ex.: G006)" value={code} onChange={(e) => setCode(e.target.value)} style={{ ...numStyle, width: 110 }} />
              <input placeholder="longitude" type="number" value={lon} onChange={(e) => setLon(e.target.value)} style={numStyle} />
              <input placeholder="latitude" type="number" value={lat} onChange={(e) => setLat(e.target.value)} style={numStyle} />
              <input placeholder="elevação (m)" type="number" value={elevation} onChange={(e) => setElevation(e.target.value)} style={numStyle} />
              <input
                placeholder="gravidade observada (mGal)"
                type="number"
                value={observedGravity}
                onChange={(e) => setObservedGravity(e.target.value)}
                style={{ ...numStyle, width: 160 }}
              />
            </div>
            {saveError && <p style={{ fontSize: ".78rem", color: "var(--bad)", margin: ".4rem 0 0" }}>{saveError}</p>}
            <button onClick={addStation} disabled={saving} style={{ ...btnStyle, marginTop: ".5rem" }}>
              {saving ? "Salvando…" : "Salvar estação"}
            </button>

            <div style={{ marginTop: ".8rem", borderTop: "1px dashed var(--border)", paddingTop: ".6rem" }}>
              <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: "0 0 .4rem" }}>
                ou importe várias de uma vez via CSV (colunas: code,lon,lat,latitude_deg,elevation_m,observed_gravity_mgal)
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
          </div>
        )}

        <div style={{ display: "flex", gap: ".5rem", alignItems: "center", margin: "1rem 0 .6rem" }}>
          <label style={{ fontSize: ".75rem", color: "var(--ink-muted)" }}>densidade (kg/m³)</label>
          <input
            type="number"
            value={density}
            onChange={(e) => setDensity(Number(e.target.value))}
            style={{ width: 90, padding: ".35rem .5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)" }}
          />
          <button onClick={runProfile} disabled={loading || stations.length === 0} style={btnStyle}>
            {loading ? "Calculando…" : "Calcular perfil"}
          </button>
        </div>
        {error && <p style={{ fontSize: ".8rem", color: "var(--bad)" }}>{error}</p>}
        {stations.length === 0 && <p style={{ fontSize: ".8rem", color: "var(--ink-muted)" }}>Nenhuma estação gravimétrica cadastrada ainda.</p>}

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
