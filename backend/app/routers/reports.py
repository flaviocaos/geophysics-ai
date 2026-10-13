from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/generate")
def generate_report(survey_id: str, result_id: str | None = None, format: str = "pdf") -> JSONResponse:
    return JSONResponse(status_code=202, content={"survey_id": survey_id, "result_id": result_id, "format": format, "status": "queued"})


@router.get("/{survey_id}/download")
def download_report(survey_id: str):
    return JSONResponse(
        status_code=501,
        content={"detail": "Geração de PDF/DOCX do relatório técnico do levantamento geofísico entra na Fase 3 — endpoint e contrato já definidos."},
    )
