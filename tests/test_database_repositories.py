import pytest

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.repositories import (
    CarRepository,
    ExperimentRepository,
    GoldSessionMetricsRepository,
    MLRunRepository,
    SessionRepository,
    SetupRepository,
    TrackRepository,
)
from ac_race_engineer.database.session import (
    create_database_engine,
    database_session,
)


def test_car_repository_create_and_update() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    try:
        with database_session(engine) as session:
            repository = CarRepository(
                session
            )

            car = repository.save(
                car_key="mazda_mx5_cup",
                name="Mazda MX-5 Cup",
                manufacturer="Mazda",
                drivetrain="RWD",
                metadata={
                    "source": "test",
                },
            )

            car_id = car.id

        with database_session(engine) as session:
            repository = CarRepository(
                session
            )

            car = repository.get_by_id(
                car_id
            )

            assert car is not None
            assert (
                car.car_key
                == "mazda_mx5_cup"
            )
            assert car.manufacturer == "Mazda"

            updated = repository.save(
                car_key="mazda_mx5_cup",
                name="Mazda MX-5 Cup ND",
                manufacturer="Mazda",
                drivetrain="RWD",
            )

            assert updated.id == car_id
            assert (
                updated.name
                == "Mazda MX-5 Cup ND"
            )

    finally:
        engine.dispose()


def test_track_repository() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    try:
        with database_session(engine) as session:
            repository = TrackRepository(
                session
            )

            track = repository.save(
                track_key="laguna_seca",
                name="WeatherTech Raceway Laguna Seca",
                layout="Full",
                length_m=3602.0,
            )

            track_id = track.id

        with database_session(engine) as session:
            repository = TrackRepository(
                session
            )

            track = repository.get_by_id(
                track_id
            )

            assert track is not None
            assert (
                track.track_key
                == "laguna_seca"
            )
            assert track.length_m == 3602.0

    finally:
        engine.dispose()


def test_setup_repository_for_car() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    try:
        with database_session(engine) as session:
            cars = CarRepository(
                session
            )
            setups = SetupRepository(
                session
            )

            car = cars.save(
                car_key="mazda_mx5_cup",
                name="Mazda MX-5 Cup",
            )

            setups.save(
                setup_key="mx5_baseline",
                car_id=car.id,
                name="Baseline",
                parameters={
                    "tyre_pressure_front": 24.5,
                    "tyre_pressure_rear": 24.0,
                },
            )

            results = setups.list_for_car(
                car.id
            )

            assert len(results) == 1
            assert (
                results[0].setup_key
                == "mx5_baseline"
            )

    finally:
        engine.dispose()


def test_database_session_rolls_back() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    try:
        with pytest.raises(
            RuntimeError
        ), database_session(
            engine
        ) as session:
            repository = CarRepository(
                session
            )

            repository.save(
                car_key="rollback_car",
                name="Rollback Car",
            )

            raise RuntimeError(
                "force rollback"
            )

        with database_session(engine) as session:
            repository = CarRepository(
                session
            )

            assert (
                repository.get_by_key(
                    "rollback_car"
                )
                is None
            )

    finally:
        engine.dispose()

def test_session_repository() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    try:
        with database_session(engine) as session:
            cars = CarRepository(session)
            tracks = TrackRepository(session)
            setups = SetupRepository(session)
            sessions = SessionRepository(session)

            car = cars.save(
                car_key="mx5",
                name="Mazda MX-5 Cup",
            )

            track = tracks.save(
                track_key="laguna_seca",
                name="Laguna Seca",
            )

            setup = setups.save(
                setup_key="baseline",
                car_id=car.id,
                name="Baseline",
                parameters={
                    "front_pressure": 24.5,
                },
            )

            record = sessions.save(
                session_id="session-001",
                car_id=car.id,
                track_id=track.id,
                setup_id=setup.id,
                session_type="practice",
                conditions={
                    "air_temp_c": 22.0,
                },
                raw_path="data/raw/session-001.jsonl",
                bronze_path="data/bronze/session-001",
                silver_path="data/silver/session-001",
            )

            assert record.id == "session-001"

        with database_session(engine) as session:
            repository = SessionRepository(session)

            record = repository.get_by_id(
                "session-001"
            )

            assert record is not None
            assert record.session_type == "practice"
            assert record.conditions == {
                "air_temp_c": 22.0,
            }

    finally:
        engine.dispose()


def test_experiment_repository() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    try:
        with database_session(engine) as session:
            cars = CarRepository(session)
            experiments = ExperimentRepository(
                session
            )

            car = cars.save(
                car_key="mx5",
                name="Mazda MX-5 Cup",
            )

            experiment = experiments.save(
                experiment_id="exp-001",
                name="Front pressure sweep",
                car_id=car.id,
                status="running",
                config={
                    "parameter": "front_pressure",
                    "values": [
                        23.0,
                        24.0,
                        25.0,
                    ],
                },
            )

            assert experiment.id == "exp-001"

        with database_session(engine) as session:
            repository = ExperimentRepository(
                session
            )

            experiment = repository.get_by_id(
                "exp-001"
            )

            assert experiment is not None
            assert experiment.status == "running"

    finally:
        engine.dispose()


def test_ml_run_repository() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    try:
        with database_session(engine) as session:
            cars = CarRepository(session)
            experiments = ExperimentRepository(
                session
            )
            runs = MLRunRepository(session)

            car = cars.save(
                car_key="mx5",
                name="Mazda MX-5 Cup",
            )

            experiment = experiments.save(
                experiment_id="exp-ml",
                name="ML experiment",
                car_id=car.id,
            )

            run = runs.save(
                run_id="run-001",
                experiment_id=experiment.id,
                model_type="random_forest",
                target="front_slip_angle_deg",
                features=[
                    "front_pressure",
                    "speed_kph",
                ],
                metrics={
                    "mae": 0.12,
                    "r2": 0.91,
                },
                artifact_path=(
                    "artifacts/run-001.joblib"
                ),
            )

            assert run.id == "run-001"

        with database_session(engine) as session:
            repository = MLRunRepository(session)

            results = repository.list_for_experiment(
                "exp-ml"
            )

            assert len(results) == 1
            assert (
                results[0].model_type
                == "random_forest"
            )
            assert results[0].metrics == {
                "mae": 0.12,
                "r2": 0.91,
            }

    finally:
        engine.dispose()


def test_gold_metrics_repository() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    try:
        with database_session(engine) as session:
            cars = CarRepository(session)
            sessions = SessionRepository(session)
            gold = GoldSessionMetricsRepository(
                session
            )

            car = cars.save(
                car_key="mx5",
                name="Mazda MX-5 Cup",
            )

            sessions.save(
                session_id="session-gold",
                car_id=car.id,
                session_type="practice",
            )

            result = gold.save(
                session_id="session-gold",
                row_count=1200,
                duration_seconds=600.0,
                metrics={
                    "avg_speed_kph": 101.4,
                    "avg_front_slip_deg": 3.2,
                },
                pipeline_version="1.0",
            )

            assert result.row_count == 1200

        with database_session(engine) as session:
            repository = (
                GoldSessionMetricsRepository(
                    session
                )
            )

            result = repository.get_for_session(
                "session-gold"
            )

            assert result is not None
            assert result.row_count == 1200
            assert result.metrics[
                "avg_speed_kph"
            ] == 101.4

    finally:
        engine.dispose()