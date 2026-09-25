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

_MODEL_REGISTRY = (
    CarRecord,
    TrackRecord,
    SetupRecord,
    SessionRecord,
    ExperimentRecord,
    MLRunRecord,
    GoldSessionMetricsRecord,
)


def create_schema() -> None:
    engine = create_database_engine()

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def main() -> None:
    create_schema()
    print("PostgreSQL schema created successfully.")


if __name__ == "__main__":
    main()

