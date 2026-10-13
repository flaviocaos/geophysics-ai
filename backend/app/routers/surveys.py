"""CRUD de levantamentos geofísicos (survey), estações gravimétricas,
sondagens elétricas (SEV) e linhas de refração sísmica — cadastro pontual
via JSON e importação em lote (CSV) das leituras de campo."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString, Point, shape
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.gravity import GravityStation
from app.models.resistivity import ResistivityArrayType, ResistivitySounding
from app.models.seismic import SeismicLine
from app.models.survey import GeophysicalSurvey
from app.schemas.survey import (
    GravityStationCreate,
    ResistivitySoundingCreate,
    SeismicLineCreate,
    SurveyCreate,
    SurveyRead,
)

router = APIRouter(prefix="/api/v1/surveys", tags=["surveys"])

# TODO (Fase 6): substituir por organização/usuário autenticados via JWT.
_DEV_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@router.post("", response_model=SurveyRead, status_code=201)
def create_survey(payload: SurveyCreate, db: Session = Depends(get_db)) -> GeophysicalSurvey:
    try:
        boundary_shape = shape(payload.boundary)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"boundary GeoJSON inválido: {exc}") from exc

    survey = GeophysicalSurvey(
        org_id=_DEV_ORG_ID,
        name=payload.name,
        boundary=from_shape(boundary_shape, srid=4326),
        survey_type=payload.survey_type,
        created_by=_DEV_USER_ID,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("", response_model=list[SurveyRead])
def list_surveys(db: Session = Depends(get_db)) -> list[GeophysicalSurvey]:
    return db.query(GeophysicalSurvey).order_by(GeophysicalSurvey.created_at.desc()).all()


@router.get("/{survey_id}", response_model=SurveyRead)
def get_survey(survey_id: uuid.UUID, db: Session = Depends(get_db)) -> GeophysicalSurvey:
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")
    return survey


@router.get("/{survey_id}/export")
def export_survey(survey_id: uuid.UUID, format: str = Query(default="geojson", pattern="^(geojson|csv)$"), db: Session = Depends(get_db)):
    """Exporta as estações gravimétricas e sondagens do levantamento em GeoJSON ou CSV."""
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")

    gravity_stations = db.query(GravityStation).filter(GravityStation.survey_id == survey_id).all()
    soundings = db.query(ResistivitySounding).filter(ResistivitySounding.survey_id == survey_id).all()

    if format == "geojson":
        features = []
        for s in gravity_stations:
            pt = to_shape(s.geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [pt.x, pt.y]},
                    "properties": {"kind": "gravity_station", "code": s.code, "observed_gravity_mgal": s.observed_gravity_mgal},
                }
            )
        for s in soundings:
            pt = to_shape(s.geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [pt.x, pt.y]},
                    "properties": {"kind": "resistivity_sounding", "code": s.code, "array_type": s.array_type.value},
                }
            )
        return {"type": "FeatureCollection", "features": features}

    lines = ["kind,code,wkt"]
    for s in gravity_stations:
        pt = to_shape(s.geom)
        lines.append(f"gravity_station,{s.code},{pt.wkt}")
    for s in soundings:
        pt = to_shape(s.geom)
        lines.append(f"resistivity_sounding,{s.code},{pt.wkt}")
    return Response(content="\n".join(lines), media_type="text/csv")


# --- Estações gravimétricas -------------------------------------------------


@router.post("/{survey_id}/gravity-stations", status_code=201)
def create_gravity_station(survey_id: uuid.UUID, payload: GravityStationCreate, db: Session = Depends(get_db)) -> dict:
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")

    station = GravityStation(
        survey_id=survey_id,
        code=payload.code,
        geom=from_shape(Point(payload.lon, payload.lat), srid=4326),
        latitude_deg=payload.latitude_deg,
        elevation_m=payload.elevation_m,
        observed_gravity_mgal=payload.observed_gravity_mgal,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return {"id": str(station.id), "code": station.code}


@router.get("/{survey_id}/gravity-stations")
def list_gravity_stations(survey_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    stations = db.query(GravityStation).filter(GravityStation.survey_id == survey_id).order_by(GravityStation.code).all()
    result = []
    for s in stations:
        pt = to_shape(s.geom)
        result.append(
            {
                "id": str(s.id),
                "code": s.code,
                "lon": pt.x,
                "lat": pt.y,
                "latitude_deg": s.latitude_deg,
                "elevation_m": s.elevation_m,
                "observed_gravity_mgal": s.observed_gravity_mgal,
            }
        )
    return result


@router.post("/{survey_id}/gravity-stations/import", status_code=201)
def import_gravity_stations(survey_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Importa estações gravimétricas em lote (CSV:
    code,lon,lat,latitude_deg,elevation_m,observed_gravity_mgal)."""
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")

    raw = file.file.read().decode("utf-8")
    text_lines = [l for l in raw.splitlines() if l.strip()]
    if not text_lines:
        raise HTTPException(status_code=422, detail="arquivo vazio")

    header = [h.strip() for h in text_lines[0].split(",")]
    required = {"code", "lon", "lat", "latitude_deg", "elevation_m", "observed_gravity_mgal"}
    if not required.issubset(set(header)):
        raise HTTPException(status_code=422, detail=f"cabeçalho deve conter {sorted(required)}")

    n_created = 0
    for line in text_lines[1:]:
        values = dict(zip(header, [v.strip() for v in line.split(",")]))
        db.add(
            GravityStation(
                survey_id=survey_id,
                code=values["code"],
                geom=from_shape(Point(float(values["lon"]), float(values["lat"])), srid=4326),
                latitude_deg=float(values["latitude_deg"]),
                elevation_m=float(values["elevation_m"]),
                observed_gravity_mgal=float(values["observed_gravity_mgal"]),
            )
        )
        n_created += 1
    db.commit()
    return {"survey_id": str(survey_id), "n_stations_created": n_created}


# --- Sondagens elétricas (SEV) ----------------------------------------------


@router.post("/{survey_id}/resistivity-soundings", status_code=201)
def create_resistivity_sounding(survey_id: uuid.UUID, payload: ResistivitySoundingCreate, db: Session = Depends(get_db)) -> dict:
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")
    try:
        array_type = ResistivityArrayType(payload.array_type.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail="array_type deve ser 'wenner' ou 'schlumberger'")

    sounding = ResistivitySounding(
        survey_id=survey_id,
        code=payload.code,
        geom=from_shape(Point(payload.lon, payload.lat), srid=4326),
        array_type=array_type,
    )
    db.add(sounding)
    db.commit()
    db.refresh(sounding)
    return {"id": str(sounding.id), "code": sounding.code, "array_type": sounding.array_type.value}


@router.get("/{survey_id}/resistivity-soundings")
def list_resistivity_soundings(survey_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    soundings = db.query(ResistivitySounding).filter(ResistivitySounding.survey_id == survey_id).order_by(ResistivitySounding.code).all()
    result = []
    for s in soundings:
        pt = to_shape(s.geom)
        result.append({"id": str(s.id), "code": s.code, "array_type": s.array_type.value, "lon": pt.x, "lat": pt.y})
    return result


# --- Linhas de refração sísmica ---------------------------------------------


@router.post("/{survey_id}/seismic-lines", status_code=201)
def create_seismic_line(survey_id: uuid.UUID, payload: SeismicLineCreate, db: Session = Depends(get_db)) -> dict:
    survey = db.get(GeophysicalSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamento não encontrado")
    if len(payload.coordinates) < 2:
        raise HTTPException(status_code=422, detail="coordinates deve ter ao menos 2 pontos (LineString)")

    line = SeismicLine(
        survey_id=survey_id,
        code=payload.code,
        geom=from_shape(LineString(payload.coordinates), srid=4326),
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return {"id": str(line.id), "code": line.code}


@router.get("/{survey_id}/seismic-lines")
def list_seismic_lines(survey_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    lines_rows = db.query(SeismicLine).filter(SeismicLine.survey_id == survey_id).order_by(SeismicLine.code).all()
    result = []
    for l in lines_rows:
        geom = to_shape(l.geom)
        result.append({"id": str(l.id), "code": l.code, "coordinates": list(geom.coords)})
    return result


