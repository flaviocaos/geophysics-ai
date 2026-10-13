"""Ferramentas expostas ao LLM via tool calling.

Cascas finas sobre `app.geophysics.*` e o banco: buscam a(s) estação(ões)/
sondagem(ns)/linha(s)/registros, chamam o cálculo determinístico e devolvem
um resumo serializável. O LLM nunca vê os dados brutos de campo (leitura
gravimétrica, tensão/corrente de SEV, tempo de primeira chegada sísmica) nem
calcula uma anomalia Bouguer, uma redução ao polo, uma resistividade
aparente ou uma profundidade de refração por conta própria — ele só decide
QUAL ferramenta chamar e com quais parâmetros, e depois interpreta o JSON já
calculado.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

import numpy as np
from sqlalchemy.orm import Session

from app.geophysics import anomaly_detection as anomaly_mod
from app.geophysics import gravity_reduction as gravity_mod
from app.geophysics import magnetic_rtp as magnetic_mod
from app.geophysics import resistivity_sounding as resistivity_mod
from app.geophysics import seismic_refraction as seismic_mod
from app.geophysics.stats import round_floats


def calculate_bouguer_anomaly_tool(
    db: Session,
    station_id: str,
    density_kg_m3: float = gravity_mod.DEFAULT_CRUSTAL_DENSITY_KG_M3,
) -> dict:
    """Redução Bouguer simples de UMA estação gravimétrica já cadastrada
    (leitura observada + latitude + elevação vêm do banco)."""
    from app.models.gravity import GravityStation
    from geoalchemy2.shape import to_shape

    station = db.get(GravityStation, uuid.UUID(station_id))
    if station is None:
        return {"error": f"estação gravimétrica não encontrada: {station_id}"}

    result = gravity_mod.calculate_bouguer_anomaly(
        observed_gravity_mgal=station.observed_gravity_mgal,
        latitude_deg=station.latitude_deg,
        elevation_m=station.elevation_m,
        density_kg_m3=density_kg_m3,
    )
    pt = to_shape(station.geom)
    return round_floats({"station_id": station_id, "station_code": station.code, "lon": pt.x, "lat": pt.y, **result})


def calculate_magnetic_rtp_tool(
    db: Session,
    grid: list[list[float]],
    pixel_size_m: float,
    inclination_deg: float,
    declination_deg: float,
    inclination_magnetization_deg: float | None = None,
    declination_magnetization_deg: float | None = None,
) -> dict:
    """Redução ao polo (RTP) de uma grade de anomalia magnética de campo
    total, informada diretamente (ex.: exportada de uma camada raster já
    carregada)."""
    try:
        result = magnetic_mod.reduce_to_pole(
            np.asarray(grid, dtype=np.float64),
            pixel_size_m=pixel_size_m,
            inclination_deg=inclination_deg,
            declination_deg=declination_deg,
            inclination_magnetization_deg=inclination_magnetization_deg,
            declination_magnetization_deg=declination_magnetization_deg,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    # a grade RTP completa pode ser grande — resumida para o agente (o raster
    # completo continua disponível via create_map_layer/RasterLayer).
    summary = {k: v for k, v in result.items() if k != "rtp_grid"}
    summary["rtp_grid_shape"] = result["shape"]
    return round_floats(summary)


def calculate_resistivity_sounding_tool(db: Session, sounding_id: str) -> dict:
    """Curva de resistividade aparente vs. espaçamento de UMA sondagem
    elétrica vertical (SEV) já cadastrada, a partir das leituras de campo
    registradas (`ResistivityReading`)."""
    from app.models.resistivity import ResistivityReading, ResistivitySounding

    sounding = db.get(ResistivitySounding, uuid.UUID(sounding_id))
    if sounding is None:
        return {"error": f"sondagem não encontrada: {sounding_id}"}

    readings = (
        db.query(ResistivityReading)
        .filter(ResistivityReading.sounding_id == sounding.id)
        .order_by(ResistivityReading.spacing_m, ResistivityReading.current_spacing_m)
        .all()
    )
    if len(readings) < 2:
        return {"error": f"sondagem {sounding_id} tem menos de 2 leituras"}

    readings_payload = [
        {
            "spacing_m": r.spacing_m,
            "current_spacing_m": r.current_spacing_m,
            "potential_spacing_m": r.potential_spacing_m,
            "voltage_v": r.voltage_v,
            "current_a": r.current_ma / 1000.0,
        }
        for r in readings
    ]

    try:
        result = resistivity_mod.compute_sounding_curve(sounding.array_type.value, readings_payload)
    except ValueError as exc:
        return {"error": str(exc)}

    return round_floats({"sounding_id": sounding_id, "sounding_code": sounding.code, **result})


def interpret_seismic_refraction_tool(db: Session, line_id: str) -> dict:
    """Interpretação de refração sísmica de 2 camadas (método da distância
    de cruzamento) de UMA linha já cadastrada, a partir das leituras de
    primeira chegada registradas (`SeismicReading`)."""
    from app.models.seismic import SeismicLine, SeismicReading

    line = db.get(SeismicLine, uuid.UUID(line_id))
    if line is None:
        return {"error": f"linha sísmica não encontrada: {line_id}"}

    readings = db.query(SeismicReading).filter(SeismicReading.line_id == line.id).order_by(SeismicReading.offset_m).all()
    if len(readings) < 4:
        return {"error": f"linha {line_id} tem menos de 4 leituras de primeira chegada"}

    offsets = [r.offset_m for r in readings]
    times_ms = [r.first_arrival_time_ms for r in readings]
    is_direct = [r.is_direct_wave for r in readings]
    is_direct_wave = is_direct if all(v is not None for v in is_direct) else None

    try:
        result = seismic_mod.interpret_two_layer_refraction(offsets, times_ms, is_direct_wave=is_direct_wave)
    except ValueError as exc:
        return {"error": str(exc)}

    return round_floats({"line_id": line_id, "line_code": line.code, **result})


def detect_anomalies_tool(
    db: Session,
    grid: list[list[float]],
    threshold_sigma: float = 2.0,
    direction: str = "both",
    pixel_size_m: float = 1.0,
) -> dict:
    """Delimita manchas anômalas (candidatas a corpo-fonte) numa grade
    residual (gravimétrica ou magnética já reduzida), informada diretamente."""
    try:
        result = anomaly_mod.detect_anomalous_patches(
            np.asarray(grid, dtype=np.float64), threshold_sigma=threshold_sigma, direction=direction, pixel_size_m=pixel_size_m
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return round_floats(result)


def query_postgis(db: Session, survey_id: str, filters: dict | None = None) -> dict:
    """Lista as estações/sondagens/linhas cadastradas num levantamento geofísico."""
    from geoalchemy2.shape import to_shape

    from app.models.gravity import GravityStation
    from app.models.resistivity import ResistivitySounding
    from app.models.seismic import SeismicLine

    sid = uuid.UUID(survey_id)

    gravity_stations = db.query(GravityStation).filter(GravityStation.survey_id == sid).order_by(GravityStation.code).all()
    soundings = db.query(ResistivitySounding).filter(ResistivitySounding.survey_id == sid).order_by(ResistivitySounding.code).all()
    lines = db.query(SeismicLine).filter(SeismicLine.survey_id == sid).order_by(SeismicLine.code).all()

    def _pt(geom):
        p = to_shape(geom)
        return {"lon": p.x, "lat": p.y}

    return {
        "gravity_stations": [
            {"id": str(s.id), "code": s.code, **_pt(s.geom), "elevation_m": s.elevation_m, "observed_gravity_mgal": s.observed_gravity_mgal}
            for s in gravity_stations
        ],
        "resistivity_soundings": [
            {"id": str(s.id), "code": s.code, "array_type": s.array_type.value, **_pt(s.geom)} for s in soundings
        ],
        "seismic_lines": [{"id": str(l.id), "code": l.code} for l in lines],
    }


def create_map_layer(db: Session, result_id: str) -> dict:
    return {"result_id": result_id, "layer_type": "geojson", "url": f"/api/v1/analysis/{result_id}/layer.geojson"}


def generate_chart(db: Session, result_id: str, chart_type: str = "sounding_curve") -> dict:
    return {"result_id": result_id, "chart_type": chart_type, "url": f"/api/v1/analysis/{result_id}/chart?type={chart_type}"}


def generate_report(db: Session, survey_id: str, result_id: str | None = None, format: str = "pdf") -> dict:
    return {
        "survey_id": survey_id,
        "result_id": result_id,
        "format": format,
        "status": "queued",
        "download_url": f"/api/v1/reports/{survey_id}/download?format={format}",
    }


# ---------------------------------------------------------------------------
# Esquema de ferramentas exposto ao LLM (formato Anthropic tool-calling)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "calculate_bouguer_anomaly",
        "description": (
            "Reduz uma leitura gravimétrica bruta de uma estação já cadastrada a uma anomalia "
            "Bouguer simples, via Fórmula Internacional da Gravidade 1980, correção ar-livre e "
            "correção Bouguer simples (SEM correção de terreno — limitação documentada do MVP)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "station_id": {"type": "string"},
                "density_kg_m3": {"type": "number", "default": gravity_mod.DEFAULT_CRUSTAL_DENSITY_KG_M3},
            },
            "required": ["station_id"],
        },
    },
    {
        "name": "calculate_magnetic_rtp",
        "description": (
            "Aplica a redução ao polo (RTP) a uma grade de anomalia magnética de campo total via "
            "filtro espectral (FFT), tornando a anomalia simétrica e centrada sobre a fonte."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "grid": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}, "description": "grade 2D (linhas x colunas) da anomalia magnética observada (nT)"},
                "pixel_size_m": {"type": "number"},
                "inclination_deg": {"type": "number"},
                "declination_deg": {"type": "number"},
                "inclination_magnetization_deg": {"type": "number", "description": "opcional, se remanência conhecida"},
                "declination_magnetization_deg": {"type": "number", "description": "opcional, se remanência conhecida"},
            },
            "required": ["grid", "pixel_size_m", "inclination_deg", "declination_deg"],
        },
    },
    {
        "name": "calculate_resistivity_sounding",
        "description": (
            "Calcula a curva de resistividade aparente vs. espaçamento de uma sondagem elétrica "
            "vertical (Wenner ou Schlumberger) já cadastrada, a partir das leituras de campo."
        ),
        "input_schema": {"type": "object", "properties": {"sounding_id": {"type": "string"}}, "required": ["sounding_id"]},
    },
    {
        "name": "interpret_seismic_refraction",
        "description": (
            "Interpreta uma linha de refração sísmica de 2 camadas (método da distância de "
            "cruzamento) a partir das leituras de primeira chegada já cadastradas, recuperando V1, "
            "V2 e a profundidade da interface."
        ),
        "input_schema": {"type": "object", "properties": {"line_id": {"type": "string"}}, "required": ["line_id"]},
    },
    {
        "name": "detect_anomalies",
        "description": (
            "Delimita manchas anômalas (candidatas a corpo-fonte) numa grade residual gravimétrica "
            "ou magnética já reduzida, por limiar de z-score e extração de componentes conexos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "grid": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                "threshold_sigma": {"type": "number", "default": 2.0},
                "direction": {"type": "string", "enum": ["both", "high", "low"], "default": "both"},
                "pixel_size_m": {"type": "number", "default": 1.0},
            },
            "required": ["grid"],
        },
    },
    {
        "name": "query_postgis",
        "description": "Lista as estações gravimétricas, sondagens elétricas e linhas sísmicas cadastradas num levantamento.",
        "input_schema": {
            "type": "object",
            "properties": {"survey_id": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["survey_id"],
        },
    },
    {
        "name": "create_map_layer",
        "description": "Gera a camada de mapa (GeoJSON) de um resultado de análise já calculado.",
        "input_schema": {"type": "object", "properties": {"result_id": {"type": "string"}}, "required": ["result_id"]},
    },
    {
        "name": "generate_chart",
        "description": "Gera a especificação de um gráfico (Plotly) para um resultado de análise (ex.: curva de sondagem, dromocrônica).",
        "input_schema": {
            "type": "object",
            "properties": {"result_id": {"type": "string"}, "chart_type": {"type": "string"}},
            "required": ["result_id"],
        },
    },
    {
        "name": "generate_report",
        "description": "Gera o relatório técnico do levantamento geofísico (PDF/DOCX), opcionalmente centrado em um resultado específico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "survey_id": {"type": "string"},
                "result_id": {"type": "string"},
                "format": {"type": "string", "enum": ["pdf", "docx"]},
            },
            "required": ["survey_id"],
        },
    },
]

TOOL_IMPLEMENTATIONS: dict[str, Callable[..., dict]] = {
    "calculate_bouguer_anomaly": calculate_bouguer_anomaly_tool,
    "calculate_magnetic_rtp": calculate_magnetic_rtp_tool,
    "calculate_resistivity_sounding": calculate_resistivity_sounding_tool,
    "interpret_seismic_refraction": interpret_seismic_refraction_tool,
    "detect_anomalies": detect_anomalies_tool,
    "query_postgis": query_postgis,
    "create_map_layer": create_map_layer,
    "generate_chart": generate_chart,
    "generate_report": generate_report,
}
