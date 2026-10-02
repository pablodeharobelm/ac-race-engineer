from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ac_race_engineer.database.base import Base


class CarRecord(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    car_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    drivetrain: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TrackRecord(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    track_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
    )

    layout: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    length_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SetupRecord(Base):
    __tablename__ = "setups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    setup_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )

    car_id: Mapped[int] = mapped_column(
        ForeignKey("cars.id"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
    )

    parameters: Mapped[dict] = mapped_column(
        JSON,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    car_id: Mapped[int] = mapped_column(
        ForeignKey("cars.id"),
        index=True,
    )

    track_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracks.id"),
        nullable=True,
        index=True,
    )

    setup_id: Mapped[int | None] = mapped_column(
        ForeignKey("setups.id"),
        nullable=True,
        index=True,
    )

    session_type: Mapped[str] = mapped_column(
        String(32),
    )

    source: Mapped[str] = mapped_column(
        String(32),
        default="simulator",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conditions: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    raw_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    bronze_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    silver_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ExperimentRecord(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
    )

    car_id: Mapped[int] = mapped_column(
        ForeignKey("cars.id"),
        index=True,
    )

    track_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracks.id"),
        nullable=True,
        index=True,
    )

    baseline_setup_id: Mapped[int | None] = mapped_column(
        ForeignKey("setups.id"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="created",
    )

    config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MLRunRecord(Base):
    __tablename__ = "ml_runs"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    experiment_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiments.id"),
        nullable=True,
        index=True,
    )

    model_type: Mapped[str] = mapped_column(
        String(120),
    )

    target: Mapped[str] = mapped_column(
        String(120),
    )

    features: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    metrics: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    artifact_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class GoldSessionMetricsRecord(Base):
    __tablename__ = "gold_session_metrics"

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "sessions.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    row_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    metrics: Mapped[dict] = mapped_column(
        JSON,
    )

    pipeline_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class LapRecord(Base):
    __tablename__ = "laps"

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "lap_number",
            name="uq_laps_session_lap_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "sessions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    lap_number: Mapped[int] = mapped_column(
        Integer,
    )

    lap_time_ms: Mapped[int] = mapped_column(
        Integer,
    )

    best_lap_time_ms: Mapped[int] = mapped_column(
        Integer,
    )

    is_best: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
    )

    is_in_pit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_in_pit_lane: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SectorRecord(Base):
    __tablename__ = "sectors"

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "lap_number",
            "sector_number",
            name="uq_sectors_session_lap_sector",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "sessions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    lap_number: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    sector_index: Mapped[int] = mapped_column(
        Integer,
    )

    sector_number: Mapped[int] = mapped_column(
        Integer,
    )

    sector_time_ms: Mapped[int] = mapped_column(
        Integer,
    )

    position: Mapped[int] = mapped_column(
        Integer,
    )

    is_in_pit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_in_pit_lane: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class LapTraceRecord(Base):
    __tablename__ = "lap_traces"

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "lap_number",
            name=(
                "uq_lap_traces_session_lap_number"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "sessions.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    lap_number: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    lap_time_ms: Mapped[int] = mapped_column(
        Integer,
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
    )

    progress_start: Mapped[float] = mapped_column(
        Float,
    )

    progress_end: Mapped[float] = mapped_column(
        Float,
    )

    parquet_path: Mapped[str] = mapped_column(
        String(500),
    )

    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )