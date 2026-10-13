"use client";

import { useRef, useState } from "react";
import type { CSSProperties } from "react";
import { MagneticRtpResult, api } from "@/lib/api";

// Grade de exemplo (16x16, nT) — anomalia sintética de uma fonte pontual
// enterrada, OBSERVADA sob um campo ambiente inclinado (I=30°, D=20°) —
// visivelmente deslocada/assimétrica em relação ao centro geométrico da
// grade (a fonte real está no centro, célula [8,8]). Gerada com a mesma
// metodologia usada em `tests/test_magnetic_rtp.py` do backend. Serve como
// demonstração; use "Minha grade" para analisar dados reais.
const EXAMPLE_PIXEL_SIZE_M = 50;
const EXAMPLE_TRUE_INCLINATION_DEG = 30;
const EXAMPLE_TRUE_DECLINATION_DEG = 20;
const EXAMPLE_GRID: number[][] = [
  [24.31, 29.39, 30.3, 28.81, 24.35, 17.8, 9.64, 1.34, -5.79, -10.43, -11.82, -10.06, -5.48, 0.77, 8.33, 15.81],
  [27.99, 35.34, 38.21, 38.79, 35.96, 30.4, 22.13, 12.54, 3.17, -4.13, -7.95, -8.01, -4.44, 1.46, 9.38, 17.61],
  [32.25, 42.17, 47.14, 49.83, 48.44, 43.32, 33.88, 21.54, 8.41, -2.57, -9.03, -10.37, -6.82, -0.18, 9.15, 19.07],
  [37.27, 50.22, 57.71, 63.08, 63.71, 59.33, 48.33, 31.97, 13.25, -2.96, -12.7, -15.08, -10.81, -2.67, 8.71, 20.79],
  [42.32, 58.41, 68.63, 77.19, 80.6, 77.68, 65.12, 43.4, 16.77, -6.61, -20.17, -22.9, -16.83, -6.27, 7.76, 22.31],
  [46.92, 65.89, 78.77, 90.85, 97.85, 97.53, 84.04, 55.99, 18.97, -13.61, -31.08, -32.97, -23.86, -10.15, 6.75, 23.64],
  [50.2, 71.14, 85.92, 100.89, 111.3, 114.03, 100.3, 65.7, 16.96, -25.31, -45.26, -44.33, -30.96, -13.77, 5.77, 24.49],
  [51.55, 73.02, 88.18, 104.15, 115.96, 120.0, 105.45, 65.24, 7.22, -40.99, -59.77, -54.06, -36.18, -16.06, 5.21, 24.8],
  [50.53, 70.79, 84.39, 98.52, 108.06, 109.36, 91.55, 48.07, -11.3, -56.71, -69.85, -59.04, -38.02, -16.51, 5.11, 24.4],
  [47.27, 64.82, 75.23, 85.08, 89.21, 84.47, 62.25, 19.94, -30.92, -65.44, -71.29, -57.52, -36.06, -15.12, 5.39, 23.29],
  [42.39, 56.44, 62.99, 67.73, 65.92, 55.54, 31.54, -4.5, -41.78, -63.84, -64.38, -50.68, -31.25, -12.49, 5.83, 21.6],
  [36.78, 47.29, 50.37, 50.81, 44.82, 31.82, 9.82, -17.56, -42.32, -55.09, -53.16, -41.42, -25.27, -9.45, 6.19, 19.55],
  [31.46, 39.05, 39.71, 37.5, 29.73, 16.97, -1.01, -20.51, -36.39, -43.66, -41.19, -31.99, -19.26, -6.43, 6.53, 17.59],
  [27.06, 32.56, 31.94, 28.58, 20.76, 9.61, -4.35, -18.15, -28.62, -33.06, -30.94, -24.05, -14.23, -3.93, 6.75, 15.93],
  [24.25, 28.66, 27.79, 24.42, 17.49, 8.25, -2.61, -12.84, -20.45, -23.81, -22.52, -17.6, -10.09, -1.78, 7.16, 15.04],
  [23.05, 27.19, 26.8, 24.01, 18.16, 10.41, 1.39, -7.13, -13.72, -17.11, -16.87, -13.49, -7.59, -0.52, 7.44, 14.79],
];

function colorFor(value: number, maxAbs: number): string {
  const t = Math.max(-1, Math.min(1, value / maxAbs));
  if (t >= 0) {
    const g = Math.round(120 + t * 100);
    return `rgb(${255 - Math.round(t * 60)},${g},80)`;
  }
  const b = Math.round(120 + -t * 100);
  return `rgb(80,${120 + Math.round(t * 60)},${b})`;
}

function Heatmap({ grid }: { grid: number[][] }) {
  const maxAbs = Math.max(...grid.flat().map((v) => Math.abs(v)), 1);
  const cell = Math.max(4, Math.min(14, Math.floor(200 / Math.max(grid.length, grid[0]?.length ?? 1))));
  return (
    <svg width={(grid[0]?.length ?? 0) * cell} height={grid.length * cell}>
      {grid.map((row, r) =>
        row.map((v, c) => <rect key={`${r}-${c}`} x={c * cell} y={r * cell} width={cell} height={cell} fill={colorFor(v, maxAbs)} />)
      )}
    </svg>
  );
}

function parseGridText(text: string): number[][] | null {
  const rows = text
    .split("\n")
    .map((row) => row.trim())
    .filter((row) => row.length > 0)
    .map((row) => row.split(",").map((v) => Number(v.trim())));
  if (rows.length === 0) return null;
  const width = rows[0].length;
  const valid = rows.every((row) => row.length === width && row.every((v) => !Number.isNaN(v)));
  return valid ? rows : null;
}

export default function MagneticPanel() {
  const [mode, setMode] = useState<"example" | "custom">("example");
  const [customGridText, setCustomGridText] = useState("");
  const [pixelSize, setPixelSize] = useState(EXAMPLE_PIXEL_SIZE_M);
  const [inclination, setInclination] = useState(EXAMPLE_TRUE_INCLINATION_DEG);
  const [declination, setDeclination] = useState(EXAMPLE_TRUE_DECLINATION_DEG);
  const [result, setResult] = useState<MagneticRtpResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeGrid = mode === "example" ? EXAMPLE_GRID : parseGridText(customGridText);

  const handleFile = async (file: File) => {
    const text = await file.text();
    setCustomGridText(text.trim());
  };

  const run = () => {
    if (!activeGrid) {
      setError("Grade inválida — confira se todas as linhas têm o mesmo número de valores separados por vírgula.");
      return;
    }
    setLoading(true);
    setError(null);
    api
      .calculateMagneticRtp(activeGrid, pixelSize, inclination, declination)
      .then(setResult)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  return (
    <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <section>
        <h3 style={{ fontSize: ".85rem", margin: "0 0 .5rem", color: "var(--ink-muted)" }}>Redução ao polo (RTP)</h3>

        <div style={{ display: "flex", gap: "0", marginBottom: ".7rem", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden", width: "fit-content" }}>
          <button onClick={() => setMode("example")} style={modeBtn(mode === "example")}>
            Grade de exemplo
          </button>
          <button onClick={() => setMode("custom")} style={modeBtn(mode === "custom")}>
            Minha grade
          </button>
        </div>

        {mode === "example" && (
          <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: "0 0 .6rem", lineHeight: 1.4 }}>
            Grade sintética de demonstração: anomalia de uma fonte pontual sob a célula central (linha 8, coluna 8),
            observada sob campo inclinado (I={EXAMPLE_TRUE_INCLINATION_DEG}°, D={EXAMPLE_TRUE_DECLINATION_DEG}°).
            Com a inclinação/declinação corretas, o pico RTP deve cair em [8, 8].
          </p>
        )}

        {mode === "custom" && (
          <div style={addBox}>
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", margin: "0 0 .4rem" }}>
              Cole ou importe sua grade de valores de campo magnético (nT), uma linha da grade por linha de texto,
              valores separados por vírgula — todas as linhas com o mesmo número de colunas.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt"
              onChange={(e) => e.target.files && e.target.files[0] && handleFile(e.target.files[0])}
              style={{ fontSize: ".78rem", color: "var(--ink-muted)", marginBottom: ".5rem" }}
            />
            <textarea
              value={customGridText}
              onChange={(e) => setCustomGridText(e.target.value)}
              rows={6}
              placeholder={"12.3,14.1,...\n15.0,18.2,...\n..."}
              style={{ width: "100%", padding: ".5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--ink)", fontFamily: "monospace", fontSize: ".76rem" }}
            />
            {customGridText && !activeGrid && (
              <p style={{ fontSize: ".76rem", color: "var(--bad)", margin: ".4rem 0 0" }}>
                Grade inválida — confira se todas as linhas têm o mesmo número de valores numéricos.
              </p>
            )}
          </div>
        )}

        {activeGrid && (
          <div style={{ marginTop: ".8rem" }}>
            <p style={{ fontSize: ".7rem", color: "var(--ink-muted)", margin: "0 0 .3rem" }}>grade observada ({activeGrid.length}×{activeGrid[0]?.length ?? 0})</p>
            <Heatmap grid={activeGrid} />
          </div>
        )}

        <div style={{ display: "flex", gap: ".6rem", marginTop: ".8rem", alignItems: "flex-end", flexWrap: "wrap" }}>
          <label style={fieldLabel}>
            tamanho do pixel (m)
            <input type="number" value={pixelSize} onChange={(e) => setPixelSize(Number(e.target.value))} style={numStyle} />
          </label>
          <label style={fieldLabel}>
            inclinação (°)
            <input type="number" value={inclination} onChange={(e) => setInclination(Number(e.target.value))} style={numStyle} />
          </label>
          <label style={fieldLabel}>
            declinação (°)
            <input type="number" value={declination} onChange={(e) => setDeclination(Number(e.target.value))} style={numStyle} />
          </label>
          <button onClick={run} disabled={loading} style={btnStyle}>
            {loading ? "Calculando…" : "Reduzir ao polo"}
          </button>
        </div>

        {error && <p style={{ fontSize: ".8rem", color: "var(--bad)", marginTop: ".5rem" }}>{error}</p>}

        {result && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: ".4rem", marginTop: ".8rem", fontSize: ".76rem" }}>
              <Tile label="pico (linha,col)" value={`${result.peak_row}, ${result.peak_col}`} />
              <Tile label="valor de pico (nT)" value={result.peak_value_nt.toFixed(2)} />
              <Tile label="magnetização" value={result.assumed_purely_induced_magnetization ? "induzida (assumida)" : "informada"} />
            </div>
            {result.low_inclination_warning && (
              <p style={{ fontSize: ".76rem", color: "var(--warn)", marginTop: ".5rem" }}>
                ⚠ inclinação baixa — o filtro pode estar amplificando ruído (ver limitations).
              </p>
            )}
            <p style={{ fontSize: ".72rem", color: "var(--ink-muted)", marginTop: ".5rem", lineHeight: 1.5 }}>{result.limitations}</p>
          </>
        )}
      </section>
    </div>
  );
}

function modeBtn(active: boolean): CSSProperties {
  return {
    padding: ".45rem .8rem",
    background: active ? "var(--surface-2)" : "transparent",
    border: "none",
    color: active ? "var(--ink)" : "var(--ink-muted)",
    fontSize: ".76rem",
    fontWeight: 600,
    cursor: "pointer",
  };
}

const fieldLabel: CSSProperties = {
  fontSize: ".75rem",
  color: "var(--ink-muted)",
  display: "flex",
  flexDirection: "column",
  gap: ".2rem",
};

const numStyle: CSSProperties = {
  padding: ".35rem .5rem",
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--ink)",
  width: 90,
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

const addBox: CSSProperties = {
  padding: ".8rem",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  marginBottom: ".6rem",
};

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: ".5rem .6rem" }}>
      <div style={{ fontSize: ".65rem", color: "var(--ink-muted)" }}>{label}</div>
      <div style={{ fontSize: ".85rem", fontWeight: 600, marginTop: ".1rem" }}>{value}</div>
    </div>
  );
}
