"""Capture two synthetic laps into the same catalog used by the local API."""

import argparsefrom collections.abc import Sequencefrom pathlib import Pathfrom sqlalchemy import Enginefrom ac_race_engineer.database.base import Basefrom ac_race_engineer.database.race_engineer_analyses import race_engineer_analysis_metadatafrom ac_race_engineer.database.session import create_database_engine, database_sessionfrom ac_race_engineer.telemetry.assetto_corsa.capture_runner import (    AssettoCorsaCaptureRunner,    CaptureStatistics,)from ac_race_engineer.telemetry.assetto_corsa.demo_backend import DemoAssettoCorsaBackendfrom ac_race_engineer.telemetry.assetto_corsa.persistence import AssettoCorsaPersistenceServicefrom ac_race_engineer.telemetry.assetto_corsa.source import AssettoCorsaSourcedef capture_demo_session(
    engine: Engine, *, trace_directory: str | Path = "data/silver/lap_traces", lap_count: int = 2,
) -> tuple[str, CaptureStatistics]:
    backend = DemoAssettoCorsaBackend(lap_count=lap_count)
    source = AssettoCorsaSource(backend, stale_timeout_seconds=None)
    with database_session(engine) as session:
        runner = AssettoCorsaCaptureRunner(
            source=source,
            persistence=AssettoCorsaPersistenceService(
                session, trace_directory=trace_directory, commit_on_drain=True,
            ),
        )
        result = runner.run(samples=backend.sample_count, interval_seconds=0)
    return source.last_completed_session.session_id, result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture a baseline and a slower synthetic lap")
    parser.add_argument("--init-db", action="store_true", help="Initialize a local SQLite demo database")
    parser.add_argument("--trace-directory", default="data/silver/lap_traces")
    parser.add_argument("--laps", type=int, choices=range(2, 21), default=2, help="Número de vueltas simuladas, de 2 a 20")
    args = parser.parse_args(argv)
    engine = create_database_engine()
    try:
        if args.init_db:
            if engine.dialect.name != "sqlite":
                parser.error("--init-db is only for SQLite. Use Alembic migrations for PostgreSQL.")
            Base.metadata.create_all(engine)
            race_engineer_analysis_metadata.create_all(engine)
        session_id, result = capture_demo_session(engine, trace_directory=args.trace_directory, lap_count=args.laps)
        print(f"Demo session: {session_id}")
        print(f"Captured {result.frames_read} frames, {result.laps_saved} laps, {result.traces_saved} traces.")
        print("Abre Mis sesiones para revisar la evolución y comparar las vueltas.")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
