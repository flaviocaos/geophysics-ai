"""Configuração do Celery para processamento assíncrono."""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("geophysics_ai", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="run_magnetic_rtp_job", bind=True)
def run_magnetic_rtp_job(
    self,
    grid: list,
    pixel_size_m: float,
    inclination_deg: float,
    declination_deg: float,
) -> dict:
    """Tarefa assíncrona: roda a redução ao polo fora do ciclo de requisição
    HTTP — útil para grades grandes (RTP via FFT é O(n log n), mas grades de
    alta resolução ainda se beneficiam de processamento em segundo plano)."""
    from app.agent.tools import calculate_magnetic_rtp_tool
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        return calculate_magnetic_rtp_tool(
            db=db, grid=grid, pixel_size_m=pixel_size_m, inclination_deg=inclination_deg, declination_deg=declination_deg
        )
    finally:
        db.close()
