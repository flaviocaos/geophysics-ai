"""Camadas raster derivadas de processamento geofísico (anomalia Bouguer,
anomalia magnética observada, anomalia reduzida ao polo) — o produto de
grade regular consumido/gerado por `app.geophysics.gravity_reduction` e
`app.geophysics.magnetic_rtp`. O arquivo raster em si (GeoTIFF) fica no
armazenamento de objetos (`storage_uri`); esta tabela guarda os metadados
necessários para localizá-lo e interpretá-lo."""
import enum
import uuid
from datetime import date as date_type, datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RasterLayerType(str, enum.Enum):
    BOUGUER_ANOMALY = "bouguer_anomaly"
    MAGNETIC_ANOMALY = "magnetic_anomaly"
    RTP_ANOMALY = "rtp_anomaly"


class RasterLayer(Base):
    __tablename__ = "raster_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    layer_type: Mapped[RasterLayerType] = mapped_column(Enum(RasterLayerType))
    reference_date: Mapped[date_type] = mapped_column(Date)
    pixel_size_m: Mapped[float] = mapped_column(Float)
    footprint: Mapped[str | None] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    storage_uri: Mapped[str] = mapped_column(String(500))
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["GeophysicalSurvey"] = relationship()
