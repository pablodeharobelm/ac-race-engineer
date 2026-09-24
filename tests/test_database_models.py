from sqlalchemy import inspect

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
    CarRecord,
    ExperimentRecord,
    GoldSessionMetricsRecord,
    MLRunRecord,
    SessionRecord,
    SetupRecord,
    TrackRecord,
)
from ac_race_engineer.database.session import (
    create_database_engine,
)

_MODELS = (
    CarRecord,
    TrackRecord,
    SetupRecord,
    SessionRecord,
    ExperimentRecord,
    MLRunRecord,
    GoldSessionMetricsRecord,
)


def test_database_schema_creation() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    try:
        Base.metadata.create_all(engine)

        inspector = inspect(engine)

        tables = set(
            inspector.get_table_names()
        )

        assert tables == {
            "cars",
            "tracks",
            "setups",
            "sessions",
            "experiments",
            "ml_runs",
            "gold_session_metrics",
        }

    finally:
        engine.dispose()


def test_session_foreign_keys() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    try:
        Base.metadata.create_all(engine)

        inspector = inspect(engine)

        foreign_keys = inspector.get_foreign_keys(
            "sessions"
        )

        referenced_tables = {
            key["referred_table"]
            for key in foreign_keys
        }

        assert referenced_tables == {
            "cars",
            "tracks",
            "setups",
        }

    finally:
        engine.dispose()