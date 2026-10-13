"""Ponto de entrada da API do Geophysics AI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analysis, chat, field_readings, reports, surveys

settings = get_settings()

app = FastAPI(
    title="Geophysics AI",
    description="Redução e interpretação de dados brutos de levantamento geofísico de campo — gravimetria (anomalia Bouguer), magnetometria (redução ao polo), eletrorresistividade (SEV) e sísmica de refração",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(surveys.router)
app.include_router(field_readings.router)
app.include_router(analysis.router)
app.include_router(chat.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "geophysics-ai-backend", "environment": settings.environment}
