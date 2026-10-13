"""Sondagens elétricas verticais (SEV) e suas leituras de campo — consumidas
por `app.geophysics.resistivity_sounding`."""
import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResistivityArrayType(str, enum.Enum):
    WENNER = "wenner"
    SCHLUMBERGER = "schlumberger"


class ResistivitySounding(Base):
    """Uma sondagem elétrica vertical (SEV) — um ponto de campo onde uma
    sequência de leituras com espaçamentos crescentes foi feita (Wenner ou
    Schlumberger)."""

    __tablename__ = "resistivity_soundings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # ex.: "SEV-01"
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    array_type: Mapped[ResistivityArrayType] = mapped_column(Enum(ResistivityArrayType))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["GeophysicalSurvey"] = relationship()
    readings: Mapped[list["ResistivityReading"]] = relationship(back_populates="sounding", cascade="all, delete-orphan")


class ResistivityReading(Base):
    """Uma leitura individual (um espaçamento) de uma sondagem elétrica
    vertical: tensão medida e corrente injetada, mais a geometria do
    arranjo naquele espaçamento (Wenner usa `spacing_m`; Schlumberger usa
    `current_spacing_m`/`potential_spacing_m`)."""

    __tablename__ = "resistivity_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sounding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resistivity_soundings.id"))
    spacing_m: Mapped[float | None] = mapped_column(Float)  # Wenner: "a"
    current_spacing_m: Mapped[float | None] = mapped_column(Float)  # Schlumberger: "L" (AB)
    potential_spacing_m: Mapped[float | None] = mapped_column(Float)  # Schlumberger: "l" (MN)
    voltage_v: Mapped[float] = mapped_column(Float)
    current_ma: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sounding: Mapped["ResistivitySounding"] = relationship(back_populates="readings")
