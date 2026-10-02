from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    func,
)

race_engineer_analysis_metadata = MetaData()


race_engineer_analyses_table = Table(
    "race_engineer_analyses",
    race_engineer_analysis_metadata,
    Column(
        "id",
        String(64),
        primary_key=True,
    ),
    Column(
        "session_id",
        String(64),
        nullable=True,
    ),
    Column(
        "reference_lap_number",
        Integer,
        nullable=False,
    ),
    Column(
        "target_lap_number",
        Integer,
        nullable=False,
    ),
    Column(
        "trend",
        String(32),
        nullable=False,
    ),
    Column(
        "total_time_lost_seconds",
        Float,
        nullable=False,
    ),
    Column(
        "total_time_gained_seconds",
        Float,
        nullable=False,
    ),
    Column(
        "net_time_delta_seconds",
        Float,
        nullable=False,
    ),
    Column(
        "primary_problem_corner",
        Integer,
        nullable=True,
    ),
    Column(
        "recommendations_generated",
        Integer,
        nullable=False,
    ),
    Column(
        "recommendations_selected",
        Integer,
        nullable=False,
    ),
    Column(
        "recommendations_suppressed",
        Integer,
        nullable=False,
    ),
    Column(
        "report_json",
        JSON,
        nullable=False,
    ),
    Column(
        "explanation_json",
        JSON,
        nullable=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)


Index(
    "ix_race_engineer_analyses_session_id",
    race_engineer_analyses_table.c.session_id,
)

Index(
    "ix_race_engineer_analyses_created_at",
    race_engineer_analyses_table.c.created_at,
)


@dataclass(frozen=True)
class RaceEngineerAnalysisRecord:
    id: str

    session_id: str | None

    reference_lap_number: int
    target_lap_number: int

    trend: str

    total_time_lost_seconds: float
    total_time_gained_seconds: float
    net_time_delta_seconds: float

    primary_problem_corner: int | None

    recommendations_generated: int
    recommendations_selected: int
    recommendations_suppressed: int

    report_json: dict
    explanation_json: dict | None

    created_at: datetime