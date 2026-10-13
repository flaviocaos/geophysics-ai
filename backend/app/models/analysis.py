"""Resultados de análise — versionados, nunca recalculados silenciosamente."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisResultType(str, enum.Enum):
    GRAVITY_REDUCTION = "gravity_reduction"
    MAGNETIC_RTP = "magnetic_rtp"
    RESISTIVITY_SOUNDING = "resistivity_sounding"
    SEISMIC_REFRACTION = "seismic_refraction"
    ANOMALY_DETECTION = "anomaly_detection"


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    result_type: Mapped[AnalysisResultType] = mapped_column(Enum(AnalysisResultType))
    entity_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
