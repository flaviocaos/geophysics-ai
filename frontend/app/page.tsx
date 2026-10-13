"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, GeophysicalSurvey, PolygonGeoJSON } from "@/lib/api";

const SURVEY_TYPES = [
  { value: "multi-metodo", label: "Multi-método" },
  { value: "gravimetria", label: "Gravimetria" },
  { value: "magnetometria", label: "Magnetometria" },
  { value: "resistividade", label: "Resistividade (SEV)" },
  { value: "sismica", label: "Sísmica de refração" },
];

// Centro padrão (Brasília) — apenas um ponto de partida; o usuário pode
// trocar as coordenadas pelo local real do levantamento. O polígono é só
// um retângulo aproximado em torno do centro: os pontos de coleta reais
// (estações, sondagens, linhas) são cadastrados depois, cada um com sua
// própria coordenada exata.
const DEFAULT_CENTER_LON = -47.9;
const DEFAULT_CENTER_LAT = -15.78;
const DEFAULT_RADIUS_KM = 5;

function buildSquareBoundary(centerLon: number, centerLat: number, radiusKm: number): PolygonGeoJSON {
  const latDelta = radiusKm / 111;
  const lonDelta = radiusKm / (111 * Math.cos((centerLat * Math.PI) / 180) || 1);
  const minLon = centerLon - lonDelta;
  const maxLon = centerLon + lonDelta;
  const minLat = centerLat - latDelta;
  const maxLat = centerLat + latDelta;
  return {
    type: "Polygon",
    coordinates: [
      [
        [minLon, minLat],
        [maxLon, minLat],
        [maxLon, maxLat],
        [minLon, maxLat],
        [minLon, minLat],
      ],
    ],
  };
}

export default function SurveysPage() {
  const router = useRouter();
  const [surveys, setSurveys] = useState<GeophysicalSurvey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [surveyType, setSurveyType] = useState("multi-metodo");
  const [centerLon, setCenterLon] = useState(DEFAULT_CENTER_LON);
  const [centerLat, setCenterLat] = useState(DEFAULT_CENTER_LAT);
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS_KM);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const reload = () => {
    setLoading(true);
    api
      .listSurveys()
      .then(setSurveys)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) {
      setCreateError("Informe um nome para o levantamento.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const boundary = buildSquareBoundary(centerLon, centerLat, radiusKm);
      const survey = await api.createSurvey(name.trim(), boundary, surveyType);
      router.push(`/surveys/${survey.id}`);
    } catch (err) {
      setCreateError(String(err));
      setCreating(false);
    }
  };

  return (
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <p style={{ fontFamily: "monospace", fontSize: ".75rem", letterSpacing: ".08em", color: "var(--ink-muted)" }}>
        GEOPHYSICS AI
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", marginTop: ".3rem" }}>Levantamentos geofísicos</h1>
          <p style={{ color: "var(--ink-muted)", fontSize: ".9rem", marginTop: ".2rem" }}>
            Redução gravimétrica (Bouguer), redução ao polo magnética, sondagem elétrica vertical e
            refração sísmica — sempre a partir de funções determinísticas, nunca calculadas pelo LLM.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          style={{
            padding: ".6rem 1.1rem",
            background: "var(--accent)",
            border: "none",
            borderRadius: 6,
            color: "#fff",
            fontSize: ".85rem",
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          {showForm ? "Cancelar" : "+ Novo levantamento"}
        </button>
      </div>

      {showForm && (
        <section
          style={{
            marginTop: "1.2rem",
            padding: "1.2rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            display: "flex",
            flexDirection: "column",
            gap: ".8rem",
          }}
        >
          <h2 style={{ fontSize: "1rem", margin: 0 }}>Criar levantamento</h2>

          <label style={fieldLabel}>
            Nome do levantamento
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex.: Área Industrial Norte — 2026"
              style={textInput}
            />
          </label>

          <label style={fieldLabel}>
            Tipo
            <select value={surveyType} onChange={(e) => setSurveyType(e.target.value)} style={textInput}>
              {SURVEY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <div>
            <p style={{ fontSize: ".78rem", color: "var(--ink-muted)", margin: "0 0 .5rem" }}>
              Área aproximada do levantamento (você poderá cadastrar os pontos de coleta exatos — estações,
              sondagens, linhas — depois de criar o levantamento):
            </p>
            <div style={{ display: "flex", gap: ".6rem", flexWrap: "wrap" }}>
              <label style={fieldLabelInline}>
                Longitude do centro
                <input type="number" step="0.0001" value={centerLon} onChange={(e) => setCenterLon(Number(e.target.value))} style={numInput} />
              </label>
              <label style={fieldLabelInline}>
                Latitude do centro
                <input type="number" step="0.0001" value={centerLat} onChange={(e) => setCenterLat(Number(e.target.value))} style={numInput} />
              </label>
              <label style={fieldLabelInline}>
                Raio aproximado (km)
                <input type="number" step="0.1" min="0.1" value={radiusKm} onChange={(e) => setRadiusKm(Number(e.target.value))} style={numInput} />
              </label>
            </div>
          </div>

          {createError && <p style={{ fontSize: ".82rem", color: "var(--bad)", margin: 0 }}>{createError}</p>}

          <div>
            <button
              onClick={handleCreate}
              disabled={creating}
              style={{
                padding: ".6rem 1.2rem",
                background: "var(--accent)",
                border: "none",
                borderRadius: 6,
                color: "#fff",
                fontSize: ".85rem",
                fontWeight: 600,
              }}
            >
              {creating ? "Criando…" : "Criar e abrir levantamento"}
            </button>
          </div>
        </section>
      )}

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

      {!loading && !error && surveys.length === 0 && !showForm && (
        <p style={{ color: "var(--ink-muted)", marginTop: "1.5rem" }}>
          Nenhum levantamento cadastrado ainda. Clique em <strong>&ldquo;+ Novo levantamento&rdquo;</strong> acima
          para criar o primeiro.
        </p>
      )}
    </main>
  );
}

const fieldLabel: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: ".3rem",
  fontSize: ".8rem",
  color: "var(--ink-muted)",
};

const fieldLabelInline: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: ".3rem",
  fontSize: ".78rem",
  color: "var(--ink-muted)",
};

const textInput: CSSProperties = {
  padding: ".5rem .6rem",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--ink)",
  fontSize: ".88rem",
};

const numInput: CSSProperties = {
  padding: ".45rem .5rem",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--ink)",
  width: 130,
};
