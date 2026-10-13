"""Importação e consulta de leituras de campo já associadas a uma sondagem
elétrica (SEV) ou linha sísmica existente — endpoints de nível superior
porque `sounding_id`/`line_id` já identificam o levantamento pai sem
ambiguidade."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resistivity import ResistivityReading, ResistivitySounding
from app.models.seismic import SeismicLine, SeismicReading

router = APIRouter(prefix="/api/v1", tags=["field-readings"])


# --- Leituras de sondagem elétrica (SEV) ------------------------------------


@router.post("/resistivity-soundings/{sounding_id}/readings/import", status_code=201)
def import_resistivity_readings(sounding_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Importa leituras de uma SEV em lote (CSV: voltage_v,current_ma,
    spacing_m[Wenner] ou current_spacing_m,potential_spacing_m[Schlumberger])."""
    sounding = db.get(ResistivitySounding, sounding_id)
    if sounding is None:
        raise HTTPException(status_code=404, detail="Sondagem não encontrada")

    raw = file.file.read().decode("utf-8")
    text_lines = [l for l in raw.splitlines() if l.strip()]
    if not text_lines:
        raise HTTPException(status_code=422, detail="arquivo vazio")

    header = [h.strip() for h in text_lines[0].split(",")]
    required = {"voltage_v", "current_ma"}
    if not required.issubset(set(header)):
        raise HTTPException(status_code=422, detail=f"cabeçalho deve conter ao menos {sorted(required)}")

    n_created = 0
    for line in text_lines[1:]:
        values = dict(zip(header, [v.strip() for v in line.split(",")]))
        db.add(
            ResistivityReading(
                sounding_id=sounding_id,
                voltage_v=float(values["voltage_v"]),
                current_ma=float(values["current_ma"]),
                spacing_m=float(values["spacing_m"]) if values.get("spacing_m") not in (None, "") else None,
                current_spacing_m=float(values["current_spacing_m"]) if values.get("current_spacing_m") not in (None, "") else None,
                potential_spacing_m=float(values["potential_spacing_m"]) if values.get("potential_spacing_m") not in (None, "") else None,
            )
        )
        n_created += 1
    db.commit()
    return {"sounding_id": str(sounding_id), "n_readings_created": n_created}


@router.get("/resistivity-soundings/{sounding_id}/readings")
def list_resistivity_readings(sounding_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(ResistivityReading)
        .filter(ResistivityReading.sounding_id == sounding_id)
        .order_by(ResistivityReading.spacing_m, ResistivityReading.current_spacing_m)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "voltage_v": r.voltage_v,
            "current_ma": r.current_ma,
            "spacing_m": r.spacing_m,
            "current_spacing_m": r.current_spacing_m,
            "potential_spacing_m": r.potential_spacing_m,
        }
        for r in rows
    ]


# --- Leituras de primeira chegada (refração sísmica) ------------------------


@router.post("/seismic-lines/{line_id}/readings/import", status_code=201)
def import_seismic_readings(line_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Importa leituras de primeira chegada em lote (CSV:
    offset_m,first_arrival_time_ms,is_direct_wave[opcional: true/false])."""
    line = db.get(SeismicLine, line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Linha sísmica não encontrada")

    raw = file.file.read().decode("utf-8")
    text_lines = [l for l in raw.splitlines() if l.strip()]
    if not text_lines:
        raise HTTPException(status_code=422, detail="arquivo vazio")

    header = [h.strip() for h in text_lines[0].split(",")]
    required = {"offset_m", "first_arrival_time_ms"}
    if not required.issubset(set(header)):
        raise HTTPException(status_code=422, detail=f"cabeçalho deve conter ao menos {sorted(required)}")

    n_created = 0
    for line_row in text_lines[1:]:
        values = dict(zip(header, [v.strip() for v in line_row.split(",")]))
        is_direct_raw = values.get("is_direct_wave")
        is_direct = None
        if is_direct_raw not in (None, ""):
            is_direct = is_direct_raw.strip().lower() in ("true", "1", "yes", "sim")
        db.add(
            SeismicReading(
                line_id=line_id,
                offset_m=float(values["offset_m"]),
                first_arrival_time_ms=float(values["first_arrival_time_ms"]),
                is_direct_wave=is_direct,
            )
        )
        n_created += 1
    db.commit()
    return {"line_id": str(line_id), "n_readings_created": n_created}


@router.get("/seismic-lines/{line_id}/readings")
def list_seismic_readings(line_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(SeismicReading).filter(SeismicReading.line_id == line_id).order_by(SeismicReading.offset_m).all()
    return [
        {"id": str(r.id), "offset_m": r.offset_m, "first_arrival_time_ms": r.first_arrival_time_ms, "is_direct_wave": r.is_direct_wave}
        for r in rows
    ]
