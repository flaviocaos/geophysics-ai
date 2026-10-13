"""Estações gravimétricas de campo — a leitura bruta (já amarrada a uma base
absoluta) consumida por `app.geophysics.gravity_reduction`."""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GravityStation(Base):
    """Uma estação de leitura gravimétrica de campo — ponto onde o
    gravímetro foi estacionado, com a leitura observada (já calibrada) e a
    elevação/latitude necessárias para a redução Bouguer."""

    __tablename__ = "gravity_stations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # ex.: "G001"
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    latitude_deg: Mapped[float] = mapped_column(Float)
    elevation_m: Mapped[float] = mapped_column(Float)
    observed_gravity_mgal: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["GeophysicalSurvey"] = relationship()
