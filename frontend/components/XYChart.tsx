"use client";

export interface ChartSeries {
  points: { x: number; y: number }[];
  color: string;
  mode?: "line" | "scatter";
  label?: string;
}

interface XYChartProps {
  series: ChartSeries[];
  width?: number;
  height?: number;
  xLabel?: string;
  yLabel?: string;
  logX?: boolean;
  logY?: boolean;
}

const PAD_LEFT = 52;
const PAD_BOTTOM = 26;
const PAD_TOP = 10;
const PAD_RIGHT = 14;

/** Gráfico XY simples em SVG (sem dependência externa) — usado para o perfil
 * gravimétrico, a curva de sondagem elétrica (log-log) e a dromocrônica de
 * refração sísmica com os ramos ajustados sobrepostos. */
export default function XYChart({ series, width = 400, height = 220, xLabel, yLabel, logX, logY }: XYChartProps) {
  const allPoints = series.flatMap((s) => s.points);
  if (allPoints.length === 0) {
    return <div style={{ textAlign: "center", color: "var(--ink-muted)", fontSize: ".8rem", padding: "1rem" }}>Sem dados.</div>;
  }

  const tx = (v: number) => (logX ? Math.log10(Math.max(v, 1e-9)) : v);
  const ty = (v: number) => (logY ? Math.log10(Math.max(v, 1e-9)) : v);

  const xs = allPoints.map((p) => tx(p.x));
  const ys = allPoints.map((p) => ty(p.y));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  const plotWidth = width - PAD_LEFT - PAD_RIGHT;
  const plotHeight = height - PAD_TOP - PAD_BOTTOM;

  const xFor = (v: number) => PAD_LEFT + ((tx(v) - minX) / spanX) * plotWidth;
  const yFor = (v: number) => PAD_TOP + plotHeight - ((ty(v) - minY) / spanY) * plotHeight;

  return (
    <svg width={width} height={height}>
      <line x1={PAD_LEFT} y1={PAD_TOP} x2={PAD_LEFT} y2={PAD_TOP + plotHeight} stroke="var(--border)" strokeWidth={1} />
      <line x1={PAD_LEFT} y1={PAD_TOP + plotHeight} x2={PAD_LEFT + plotWidth} y2={PAD_TOP + plotHeight} stroke="var(--border)" strokeWidth={1} />

      {series.map((s, si) => {
        const sorted = [...s.points].sort((a, b) => a.x - b.x);
        if (s.mode === "scatter") {
          return (
            <g key={si}>
              {sorted.map((p, i) => (
                <circle key={i} cx={xFor(p.x)} cy={yFor(p.y)} r={3} fill={s.color} />
              ))}
            </g>
          );
        }
        const path = sorted.map((p) => `${xFor(p.x)},${yFor(p.y)}`).join(" ");
        return <polyline key={si} points={path} fill="none" stroke={s.color} strokeWidth={1.6} />;
      })}

      <text x={2} y={PAD_TOP + 6} fontSize={9} fill="var(--ink-muted)">
        {maxY.toFixed(2)}
      </text>
      <text x={2} y={PAD_TOP + plotHeight} fontSize={9} fill="var(--ink-muted)">
        {minY.toFixed(2)}
      </text>
      {yLabel && (
        <text x={2} y={PAD_TOP + 16} fontSize={9} fill="var(--ink-muted)">
          {yLabel}
          {logY ? " (log)" : ""}
        </text>
      )}
      <text x={PAD_LEFT} y={height - 4} fontSize={9} fill="var(--ink-muted)">
        {allPoints.length > 0 ? Math.min(...allPoints.map((p) => p.x)).toFixed(1) : ""}
      </text>
      <text x={PAD_LEFT + plotWidth} y={height - 4} fontSize={9} fill="var(--ink-muted)" textAnchor="end">
        {allPoints.length > 0 ? Math.max(...allPoints.map((p) => p.x)).toFixed(1) : ""}
      </text>
      {xLabel && (
        <text x={PAD_LEFT + plotWidth} y={PAD_TOP + 8} fontSize={9} fill="var(--ink-muted)" textAnchor="end">
          {xLabel}
          {logX ? " (log)" : ""}
        </text>
      )}
    </svg>
  );
}
