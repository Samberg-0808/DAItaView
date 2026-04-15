import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DataSourceType(str, enum.Enum):
    postgres = "postgres"
    mysql = "mysql"
    sqlite = "sqlite"
    csv = "csv"
    json = "json"
    parquet = "parquet"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[DataSourceType] = mapped_column(Enum(DataSourceType), nullable=False)
    # Encrypted JSON: connection params for DB sources, file path for file sources
    connection_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="source")
    gap_signals: Mapped[list["KnowledgeGapSignal"]] = relationship(back_populates="source", cascade="all, delete-orphan")


