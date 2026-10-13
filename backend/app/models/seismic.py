"""Linhas de refração sísmica e suas leituras de primeira chegada —
consumidas por `app.geophysics.seismic_refraction`."""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SeismicLine(Base):
    """Um alinhamento (spread) de refração sísmica — geofones dispostos ao
    longo de uma linha, com um ou mais pontos de tiro."""

    __tablename__ = "seismic_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # ex.: "LINHA-01"
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["GeophysicalSurvey"] = relationship()
    readings: Mapped[list["SeismicReading"]] = relationship(back_populates="line", cascade="all, delete-orphan")


class SeismicReading(Base):
    """Uma leitura de primeira chegada (offset fonte-receptor + tempo) de
    uma linha de refração — `is_direct_wave` indica a classificação de ramo
    (direto/refratado) feita pelo intérprete de campo a partir do
    sismograma, quando disponível."""

    __tablename__ = "seismic_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seismic_lines.id"))
    offset_m: Mapped[float] = mapped_column(Float)
    first_arrival_time_ms: Mapped[float] = mapped_column(Float)
    is_direct_wave: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    line: Mapped["SeismicLine"] = relationship(back_populates="readings")
