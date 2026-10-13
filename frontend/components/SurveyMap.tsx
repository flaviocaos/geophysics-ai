"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { GravityStation, ResistivitySounding, SeismicLine } from "@/lib/api";

interface SurveyMapProps {
  gravityStations: GravityStation[];
  soundings: ResistivitySounding[];
  seismicLines: SeismicLine[];
}

// Basemap real (imagem de satélite por baixo dos pontos) em vez de fundo
// preto sólido — tiles gratuitos de satélite da Esri (World Imagery),
// servidos publicamente sem necessidade de chave de API/cadastro. Faz mais
// sentido que um mapa de ruas para um app de geofísica: mostra o terreno
// real onde os dados de campo foram coletados. `glyphs` também é necessário
// para os rótulos de texto (código da estação etc.) renderizarem no mapa —
// sem isso o MapLibre reporta erro no console e não desenha texto.
const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "esri-satellite": {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar Geographics",
    },
  },
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  layers: [{ id: "esri-satellite-layer", type: "raster", source: "esri-satellite" }],
};

export default function SurveyMap({ gravityStations, soundings, seismicLines }: SurveyMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);

  const centerLonLat = useMemo<[number, number]>(() => {
    if (gravityStations.length > 0) return [gravityStations[0].lon, gravityStations[0].lat];
    if (soundings.length > 0) return [soundings[0].lon, soundings[0].lat];
    return [-47.9, -15.78];
  }, [gravityStations, soundings]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: centerLonLat,
      zoom: 12,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => setReady(true));
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;

    const gravityData: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: gravityStations.map((s) => ({
        type: "Feature",
        properties: { code: s.code, kind: "gravity" },
        geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      })),
    };
    const soundingData: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: soundings.map((s) => ({
        type: "Feature",
        properties: { code: s.code, kind: "resistivity" },
        geometry: { type: "Point", coordinates: [s.lon, s.lat] },
      })),
    };
    const lineData: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: seismicLines.map((l) => ({
        type: "Feature",
        properties: { code: l.code },
        geometry: { type: "LineString", coordinates: l.coordinates },
      })),
    };

    const upsertSource = (id: string, data: GeoJSON.FeatureCollection) => {
      const src = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(data);
      else map.addSource(id, { type: "geojson", data });
    };

    upsertSource("gravity-stations", gravityData);
    upsertSource("resistivity-soundings", soundingData);
    upsertSource("seismic-lines", lineData);

    if (!map.getLayer("seismic-lines-layer")) {
      map.addLayer({
        id: "seismic-lines-layer",
        type: "line",
        source: "seismic-lines",
        paint: { "line-color": "#d9a441", "line-width": 2 },
      });
    }
    if (!map.getLayer("gravity-stations-layer")) {
      map.addLayer({
        id: "gravity-stations-layer",
        type: "circle",
        source: "gravity-stations",
        paint: { "circle-radius": 5, "circle-color": "#3f7fd9", "circle-stroke-width": 1, "circle-stroke-color": "#0b1420" },
      });
      map.addLayer({
        id: "gravity-labels",
        type: "symbol",
        source: "gravity-stations",
        layout: { "text-field": ["get", "code"], "text-size": 10, "text-offset": [0, 1.1], "text-anchor": "top" },
        paint: { "text-color": "#e8f1fb" },
      });
    }
    if (!map.getLayer("resistivity-soundings-layer")) {
      map.addLayer({
        id: "resistivity-soundings-layer",
        type: "circle",
        source: "resistivity-soundings",
        paint: { "circle-radius": 6, "circle-color": "#4f9c7c", "circle-stroke-width": 1, "circle-stroke-color": "#0b1420" },
      });
      map.addLayer({
        id: "resistivity-labels",
        type: "symbol",
        source: "resistivity-soundings",
        layout: { "text-field": ["get", "code"], "text-size": 10, "text-offset": [0, 1.1], "text-anchor": "top" },
        paint: { "text-color": "#e8f1fb" },
      });
    }

    const allLons = [...gravityStations.map((s) => s.lon), ...soundings.map((s) => s.lon), ...seismicLines.flatMap((l) => l.coordinates.map((c) => c[0]))];
    const allLats = [...gravityStations.map((s) => s.lat), ...soundings.map((s) => s.lat), ...seismicLines.flatMap((l) => l.coordinates.map((c) => c[1]))];
    if (allLons.length > 0) {
      map.fitBounds(
        [
          [Math.min(...allLons) - 0.01, Math.min(...allLats) - 0.01],
          [Math.max(...allLons) + 0.01, Math.max(...allLats) + 0.01],
        ],
        { padding: 40, duration: 0 }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, gravityStations, soundings, seismicLines]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />

      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: ".6rem .8rem",
          fontSize: ".76rem",
          maxWidth: 260,
          display: "flex",
          flexDirection: "column",
          gap: ".2rem",
        }}
      >
        <Legend color="#3f7fd9" label="estações gravimétricas" />
        <Legend color="#4f9c7c" label="sondagens elétricas (SEV)" />
        <Legend color="#d9a441" label="linhas de refração sísmica" />
      </div>

      {gravityStations.length === 0 && soundings.length === 0 && seismicLines.length === 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--ink-muted)",
            fontSize: ".85rem",
            background: "rgba(11,20,32,0.6)",
          }}
        >
          Nenhum dado de campo cadastrado ainda para este levantamento.
        </div>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: ".4rem" }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" }} />
      <span style={{ color: "var(--ink-muted)" }}>{label}</span>
    </div>
  );
}
