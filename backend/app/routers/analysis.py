import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.tools import (
    calculate_bouguer_anomaly_tool,
    calculate_magnetic_rtp_tool,
    calculate_resistivity_sounding_tool,
    detect_anomalies_tool,
    interpret_seismic_refraction_tool,
)
from app.database import get_db
from app.models.analysis import AnalysisResult, AnalysisResultType
from app.schemas.analysis import (
    AnomalyDetectionRequest,
    BouguerAnomalyRequest,
    MagneticRtpRequest,
    ResistivitySoundingRequest,
    SeismicRefractionRequest,
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


def _persist_result(
    db: Session,
    survey_id: uuid.UUID | None,
    result_type: AnalysisResultType,
    entity_ids: list[str],
    params: dict,
    stats: dict,
    confidence: float | None,
) -> AnalysisResult:
    row = AnalysisResult(
        survey_id=survey_id,
        result_type=result_type,
        entity_ids=entity_ids,
        params=params,
        stats=stats,
        confidence=confidence,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{result_id}")
def get_analysis_result(result_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Retorna um resultado de análise persistido na íntegra."""
    row = db.get(AnalysisResult, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resultado de análise não encontrado")
    return {
        "result_id": str(row.id),
        "survey_id": str(row.survey_id) if row.survey_id else None,
        "result_type": row.result_type.value,
        "entity_ids": row.entity_ids,
        "params": row.params,
        "stats": row.stats,
        "confidence": row.confidence,
        "created_at": row.created_at.isoformat(),
    }


@router.post("/bouguer-anomaly")
def analysis_bouguer_anomaly(payload: BouguerAnomalyRequest, db: Session = Depends(get_db)) -> dict:
    stats = calculate_bouguer_anomaly_tool(db=db, station_id=payload.station_id, density_kg_m3=payload.density_kg_m3)
    if "error" in stats:
        return stats

    from app.models.gravity import GravityStation

    station = db.get(GravityStation, uuid.UUID(payload.station_id))
    row = _persist_result(
        db,
        station.survey_id,
        AnalysisResultType.GRAVITY_REDUCTION,
        [payload.station_id],
        {"density_kg_m3": payload.density_kg_m3},
        stats,
        None,
    )
    return {"result_id": str(row.id), **stats}


@router.post("/magnetic-rtp")
def analysis_magnetic_rtp(payload: MagneticRtpRequest, db: Session = Depends(get_db)) -> dict:
    stats = calculate_magnetic_rtp_tool(
        db=db,
        grid=payload.grid,
        pixel_size_m=payload.pixel_size_m,
        inclination_deg=payload.inclination_deg,
        declination_deg=payload.declination_deg,
        inclination_magnetization_deg=payload.inclination_magnetization_deg,
        declination_magnetization_deg=payload.declination_magnetization_deg,
    )
    if "error" in stats:
        return stats

    row = _persist_result(
        db,
        None,
        AnalysisResultType.MAGNETIC_RTP,
        [],
        {"pixel_size_m": payload.pixel_size_m, "inclination_deg": payload.inclination_deg, "declination_deg": payload.declination_deg},
        stats,
        None,
    )
    return {"result_id": str(row.id), **stats}


@router.post("/resistivity-sounding")
def analysis_resistivity_sounding(payload: ResistivitySoundingRequest, db: Session = Depends(get_db)) -> dict:
    stats = calculate_resistivity_sounding_tool(db=db, sounding_id=payload.sounding_id)
    if "error" in stats:
        return stats

    from app.models.resistivity import ResistivitySounding

    sounding = db.get(ResistivitySounding, uuid.UUID(payload.sounding_id))
    row = _persist_result(
        db,
        sounding.survey_id,
        AnalysisResultType.RESISTIVITY_SOUNDING,
        [payload.sounding_id],
        {},
        stats,
        None,
    )
    return {"result_id": str(row.id), **stats}


@router.post("/seismic-refraction")
def analysis_seismic_refraction(payload: SeismicRefractionRequest, db: Session = Depends(get_db)) -> dict:
    stats = interpret_seismic_refraction_tool(db=db, line_id=payload.line_id)
    if "error" in stats:
        return stats

    from app.models.seismic import SeismicLine

    line = db.get(SeismicLine, uuid.UUID(payload.line_id))
    row = _persist_result(
        db,
        line.survey_id,
        AnalysisResultType.SEISMIC_REFRACTION,
        [payload.line_id],
        {},
        stats,
        None,
    )
    return {"result_id": str(row.id), **stats}


@router.post("/anomaly-detection")
def analysis_anomaly_detection(payload: AnomalyDetectionRequest, db: Session = Depends(get_db)) -> dict:
    stats = detect_anomalies_tool(
        db=db,
        grid=payload.grid,
        threshold_sigma=payload.threshold_sigma,
        direction=payload.direction,
        pixel_size_m=payload.pixel_size_m,
    )
    if "error" in stats:
        return stats

    row = _persist_result(
        db,
        None,
        AnalysisResultType.ANOMALY_DETECTION,
        [],
        {"threshold_sigma": payload.threshold_sigma, "direction": payload.direction, "pixel_size_m": payload.pixel_size_m},
        stats,
        None,
    )
    return {"result_id": str(row.id), **stats}
