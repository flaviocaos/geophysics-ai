"""Trilha de auditoria e histórico de chat."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))  # import_data | run_analysis | export | generate_report
    entity: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geophysical_surveys.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)
    tool_calls: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
