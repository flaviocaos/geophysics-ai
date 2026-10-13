"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { GeophysicalSurvey, GravityStation, ResistivitySounding, SeismicLine, api } from "@/lib/api";
import GravityPanel from "@/components/GravityPanel";
import MagneticPanel from "@/components/MagneticPanel";
import ResistivityPanel from "@/components/ResistivityPanel";
import SeismicPanel from "@/components/SeismicPanel";
import ChatPanel from "@/components/ChatPanel";

const SurveyMap = dynamic(() => import("@/components/SurveyMap"), { ssr: false });

type Tab = "gravity" | "magnetic" | "resistivity" | "seismic" | "chat";

export default function SurveyWorkspace({ params }: { params: { id: string } }) {
  const surveyId = params.id;
  const [survey, setSurvey] = useState<GeophysicalSurvey | null>(null);
  const [gravityStations, setGravityStations] = useState<GravityStation[]>([]);
  const [soundings, setSoundings] = useState<ResistivitySounding[]>([]);
  const [seismicLines, setSeismicLines] = useState<SeismicLine[]>([]);
  const [rightTab, setRightTab] = useState<Tab>("gravity");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getSurvey(surveyId),
      api.listGravityStations(surveyId),
      api.listResistivitySoundings(surveyId),
      api.listSeismicLines(surveyId),
    ])
      .then(([s, g, r, l]) => {
        setSurvey(s);
        setGravityStations(g);
        setSoundings(r);
        setSeismicLines(l);
      })
      .catch((err) => setLoadError(String(err)));
  }, [surveyId]);

  return (
    <main style={{ display: "grid", gridTemplateColumns: "1fr 460px", gridTemplateRows: "auto 1fr", height: "100vh" }}>
      <header
        style={{
          gridColumn: "1 / -1",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: ".8rem 1.2rem",
          borderBottom: "1px solid var(--border)",
          flexWrap: "wrap",
          gap: ".5rem",
        }}
      >
        <div>
          <a href="/" style={{ fontSize: ".75rem", color: "var(--ink-muted)" }}>
            ← levantamentos
          </a>
          <h1 style={{ fontSize: "1.1rem", margin: ".1rem 0 0" }}>{survey ? survey.name : "Geophysics AI · Workspace"}</h1>
        </div>
        {loadError && <span style={{ fontSize: ".78rem", color: "var(--bad)" }}>{loadError}</span>}
      </header>

      <section style={{ gridRow: "2 / 3", borderRight: "1px solid var(--border)" }}>
        <SurveyMap gravityStations={gravityStations} soundings={soundings} seismicLines={seismicLines} />
      </section>

      <aside style={{ gridRow: "2 / 3", borderLeft: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
          <TabButton active={rightTab === "gravity"} onClick={() => setRightTab("gravity")} label="Gravimetria" />
          <TabButton active={rightTab === "magnetic"} onClick={() => setRightTab("magnetic")} label="Magnetometria" />
          <TabButton active={rightTab === "resistivity"} onClick={() => setRightTab("resistivity")} label="Resistividade" />
          <TabButton active={rightTab === "seismic"} onClick={() => setRightTab("seismic")} label="Sísmica" />
          <TabButton active={rightTab === "chat"} onClick={() => setRightTab("chat")} label="Chat" />
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {rightTab === "gravity" && <GravityPanel stations={gravityStations} />}
          {rightTab === "magnetic" && <MagneticPanel />}
          {rightTab === "resistivity" && <ResistivityPanel soundings={soundings} />}
          {rightTab === "seismic" && <SeismicPanel lines={seismicLines} />}
          {rightTab === "chat" && (
            <div style={{ height: "100%" }}>
              <ChatPanel surveyId={surveyId} />
            </div>
          )}
        </div>
      </aside>
    </main>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: ".6rem .3rem",
        background: active ? "var(--surface-2)" : "transparent",
        border: "none",
        borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
        color: active ? "var(--ink)" : "var(--ink-muted)",
        fontSize: ".72rem",
        fontWeight: 600,
      }}
    >
      {label}
    </button>
  );
}
