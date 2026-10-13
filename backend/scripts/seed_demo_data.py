"""Gera dados simulados para demonstrar o MVP sem um levantamento geofísico
real. Cria um levantamento de demonstração com:

- ~12 estações gravimétricas ao longo de um perfil, com leitura observada
  retro-calculada a partir de uma anomalia Bouguer "verdadeira" conhecida
  (um corpo de baixa densidade simulando uma cavidade/zona de alteração,
  sobreposto a um gradiente regional suave) mais ruído de leitura realista
  (~0.02 mGal) — rodar `calculate_bouguer_anomaly` em cada estação recupera
  aproximadamente essa anomalia verdadeira;
- 3 sondagens elétricas verticais (SEV, arranjo Wenner) com leituras
  crescentes em espaçamento, simulando uma transição de uma camada rasa
  resistiva (solo seco) para uma camada mais condutiva em profundidade
  (ex.: saturação/argila) — um caso clássico de curva de sondagem
  descendente (tipo H/K simplificado);
- 2 linhas de refração sísmica de 2 camadas, com V1/V2/profundidade
  "verdadeiros" distintos por linha e ruído no tempo de primeira chegada,
  já com a classificação `is_direct_wave` marcada (como viria de um
  intérprete de campo lendo o sismograma).

Uso: `python -m scripts.seed_demo_data` (a partir de `backend/`, com o banco
já inicializado via `python -m app.init_db`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point, box

from app.database import SessionLocal
from app.geophysics.gravity_reduction import (
    free_air_correction,
    normal_gravity_igf80,
    simple_bouguer_correction,
)
from app.geophysics.resistivity_sounding import wenner_geometric_factor
from app.models.gravity import GravityStation
from app.models.resistivity import ResistivityArrayType, ResistivityReading, ResistivitySounding
from app.models.seismic import SeismicLine, SeismicReading
from app.models.survey import GeophysicalSurvey

SITE_ORG_ID = "00000000-0000-0000-0000-000000000001"
SITE_USER_ID = "00000000-0000-0000-0000-000000000002"

CENTER_LON, CENTER_LAT = -47.9, -15.78
HALF_SPAN_DEG = 0.08
DENSITY_KG_M3 = 2670.0

# --- Perfil gravimétrico -----------------------------------------------------
N_GRAVITY_STATIONS = 12
PROFILE_LENGTH_M = 1100.0  # estações espaçadas a cada 100m ao longo do perfil
ANOMALY_CENTER_M = 550.0
ANOMALY_HALF_WIDTH_M = 120.0
ANOMALY_AMPLITUDE_MGAL = -14.0  # corpo de baixa densidade (ex.: cavidade cárstica) -> anomalia negativa
REGIONAL_GRADIENT_MGAL_PER_M = 0.004  # tendência regional suave sobreposta
BASE_ELEVATION_M = 820.0
GRAVITY_NOISE_SIGMA_MGAL = 0.02

# --- Sondagens elétricas verticais -------------------------------------------
SEV_SPACINGS_M = [1, 2, 4, 8, 16, 32, 64, 100]
SEV_PROFILES = {
    "SEV-01": {"rho_shallow": 800.0, "rho_deep": 60.0, "transition_spacing_m": 12.0},
    "SEV-02": {"rho_shallow": 650.0, "rho_deep": 45.0, "transition_spacing_m": 18.0},
    "SEV-03": {"rho_shallow": 900.0, "rho_deep": 80.0, "transition_spacing_m": 9.0},
}
CURRENT_MA = 20.0
RESISTIVITY_NOISE_FRACTION = 0.02

# --- Linhas de refração sísmica ----------------------------------------------
SEISMIC_LINES = {
    "LINHA-01": {"v1": 450.0, "v2": 1800.0, "depth_m": 8.0},
    "LINHA-02": {"v1": 500.0, "v2": 2400.0, "depth_m": 15.0},
}
SEISMIC_TIME_NOISE_MS = 0.4


def _true_bouguer_anomaly_mgal(distance_along_profile_m: float) -> float:
    """Anomalia Bouguer 'verdadeira' do perfil: um corpo gaussiano de baixa
    densidade sobreposto a um gradiente regional suave."""
    body = ANOMALY_AMPLITUDE_MGAL * np.exp(
        -((distance_along_profile_m - ANOMALY_CENTER_M) ** 2) / (2 * ANOMALY_HALF_WIDTH_M ** 2)
    )
    regional = REGIONAL_GRADIENT_MGAL_PER_M * distance_along_profile_m
    return float(body + regional)


def _seed_gravity_profile(db, survey_id, rng) -> None:
    spacing_m = PROFILE_LENGTH_M / (N_GRAVITY_STATIONS - 1)
    for i in range(N_GRAVITY_STATIONS):
        distance_m = i * spacing_m
        # perfil aproximadamente E-W; converte deslocamento em graus (aprox. equador ~111km/grau)
        lon = CENTER_LON - HALF_SPAN_DEG * 0.6 + (distance_m / 111_000.0)
        lat = CENTER_LAT
        elevation_m = BASE_ELEVATION_M + 3.0 * np.sin(distance_m / 300.0) + rng.normal(0, 0.5)

        true_anomaly = _true_bouguer_anomaly_mgal(distance_m)
        g_theta = normal_gravity_igf80(lat)
        fac = free_air_correction(elevation_m)
        bc = simple_bouguer_correction(elevation_m, DENSITY_KG_M3)
        # anomalia = g_obs - g_theta + fac - bc  =>  g_obs = anomalia + g_theta - fac + bc
        g_observed = true_anomaly + g_theta - fac + bc + rng.normal(0, GRAVITY_NOISE_SIGMA_MGAL)

        db.add(
            GravityStation(
                survey_id=survey_id,
                code=f"G{i + 1:03d}",
                geom=from_shape(Point(lon, lat), srid=4326),
                latitude_deg=lat,
                elevation_m=round(float(elevation_m), 3),
                observed_gravity_mgal=round(float(g_observed), 4),
            )
        )


def _seed_resistivity_soundings(db, survey_id, rng) -> None:
    for i, (code, profile) in enumerate(SEV_PROFILES.items()):
        lon = CENTER_LON + HALF_SPAN_DEG * 0.3 + i * 0.01
        lat = CENTER_LAT - HALF_SPAN_DEG * 0.4
        sounding = ResistivitySounding(
            survey_id=survey_id,
            code=code,
            geom=from_shape(Point(lon, lat), srid=4326),
            array_type=ResistivityArrayType.WENNER,
        )
        db.add(sounding)
        db.flush()

        rho_shallow = profile["rho_shallow"]
        rho_deep = profile["rho_deep"]
        transition = profile["transition_spacing_m"]

        for spacing_m in SEV_SPACINGS_M:
            # transição suave (sigmoide em log-espaçamento) de rho_shallow -> rho_deep,
            # o comportamento típico de uma curva de sondagem tipo H (camada resistiva sobre condutiva).
            t = 1.0 / (1.0 + np.exp(-(np.log(spacing_m) - np.log(transition)) * 2.5))
            rho_target = rho_shallow * (1 - t) + rho_deep * t
            rho_target *= 1 + rng.normal(0, RESISTIVITY_NOISE_FRACTION)

            k = wenner_geometric_factor(spacing_m)
            current_a = CURRENT_MA / 1000.0
            voltage_v = rho_target * current_a / k

            db.add(
                ResistivityReading(
                    sounding_id=sounding.id,
                    spacing_m=float(spacing_m),
                    voltage_v=round(float(voltage_v), 6),
                    current_ma=CURRENT_MA,
                )
            )


def _seed_seismic_lines(db, survey_id, rng) -> None:
    for i, (code, params) in enumerate(SEISMIC_LINES.items()):
        v1, v2, depth = params["v1"], params["v2"], params["depth_m"]
        lon0 = CENTER_LON - HALF_SPAN_DEG * 0.5
        lat0 = CENTER_LAT + HALF_SPAN_DEG * (0.3 + i * 0.15)
        line = SeismicLine(
            survey_id=survey_id,
            code=code,
            geom=from_shape(LineString([(lon0, lat0), (lon0 + 0.02, lat0)]), srid=4326),
        )
        db.add(line)
        db.flush()

        theta_c = np.arcsin(v1 / v2)
        x_cross = 2 * depth * np.sqrt((v2 + v1) / (v2 - v1))

        offsets_direct = np.linspace(2.0, x_cross * 0.85, 6)
        times_direct_ms = (offsets_direct / v1) * 1000.0 + rng.normal(0, SEISMIC_TIME_NOISE_MS, len(offsets_direct))

        offsets_refracted = np.linspace(x_cross * 1.15, x_cross * 3.2, 9)
        times_refracted_ms = (
            offsets_refracted / v2 + 2 * depth * np.cos(theta_c) / v1
        ) * 1000.0 + rng.normal(0, SEISMIC_TIME_NOISE_MS, len(offsets_refracted))

        for offset_m, t_ms in zip(offsets_direct, times_direct_ms):
            db.add(SeismicReading(line_id=line.id, offset_m=round(float(offset_m), 2), first_arrival_time_ms=round(float(t_ms), 3), is_direct_wave=True))
        for offset_m, t_ms in zip(offsets_refracted, times_refracted_ms):
            db.add(SeismicReading(line_id=line.id, offset_m=round(float(offset_m), 2), first_arrival_time_ms=round(float(t_ms), 3), is_direct_wave=False))


def main() -> None:
    db = SessionLocal()
    rng = np.random.default_rng(2024)

    min_lon = CENTER_LON - HALF_SPAN_DEG
    min_lat = CENTER_LAT - HALF_SPAN_DEG
    max_lon = CENTER_LON + HALF_SPAN_DEG
    max_lat = CENTER_LAT + HALF_SPAN_DEG
    boundary = box(min_lon, min_lat, max_lon, max_lat)

    survey = GeophysicalSurvey(
        org_id=SITE_ORG_ID,
        name="Levantamento Demonstração — Prospecção Multimétodo Planalto Central",
        boundary=from_shape(boundary, srid=4326),
        survey_type="multi-metodo",
        created_by=SITE_USER_ID,
    )
    db.add(survey)
    db.flush()

    _seed_gravity_profile(db, survey.id, rng)
    _seed_resistivity_soundings(db, survey.id, rng)
    _seed_seismic_lines(db, survey.id, rng)

    db.commit()

    print(f"Levantamento geofísico demo criado: {survey.id}")
    print(f"  {N_GRAVITY_STATIONS} estações gravimétricas ao longo de um perfil de {PROFILE_LENGTH_M:.0f}m")
    print(f"  anomalia Bouguer verdadeira: corpo gaussiano de {ANOMALY_AMPLITUDE_MGAL} mGal em x={ANOMALY_CENTER_M}m + gradiente regional")
    print(f"  {len(SEV_PROFILES)} sondagens elétricas verticais (Wenner), {len(SEV_SPACINGS_M)} espaçamentos cada")
    print(f"  {len(SEISMIC_LINES)} linhas de refração sísmica de 2 camadas")
    print("Use calculate_bouguer_anomaly em cada estação G001..G012 para recuperar o perfil de anomalia.")
    print("Use calculate_resistivity_sounding nas sondagens SEV-01/02/03 para ver a curva descendente (tipo H).")
    print("Use interpret_seismic_refraction em LINHA-01/02 para recuperar V1/V2/profundidade.")


if __name__ == "__main__":
    main()
