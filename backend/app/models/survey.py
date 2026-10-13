"""Organizações, usuários e levantamentos geofísicos (contêiner de trabalho).

Um `GeophysicalSurvey` é o equivalente, no Geophysics AI, ao `Reservoir` do
Reservoir AI ou à `GnssNetwork` do GNSS AI: a área de um levantamento
geofísico de campo (gravimetria, magnetometria, eletrorresistividade e/ou
sísmica de refração) — distinto do domínio do Geology AI, que trata de
sensoriamento remoto/geologia estrutural sobre rasters já classificados, não
de redução/inversão de dados brutos de instrumento geofísico de campo."""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="trial")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    surveys: Mapped[list["GeophysicalSurvey"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="analista")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="users")


class GeophysicalSurvey(Base):
    """Área de estudo (contêiner de trabalho) — um levantamento geofísico de
    campo (gravimetria/magnetometria/eletrorresistividade/sísmica de
    refração) sobre uma área delimitada, análogo à `GnssNetwork` do GNSS AI
    ou ao `Reservoir` do Reservoir AI."""

    __tablename__ = "geophysical_surveys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    boundary: Mapped[str] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    survey_type: Mapped[str] = mapped_column(String(50), default="multi-metodo")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="surveys")
