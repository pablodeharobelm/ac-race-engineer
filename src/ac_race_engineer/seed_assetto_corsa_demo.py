from datetime import datetime, timedelta, timezone

from ac_race_engineer.database.session import (
    create_database_engine,
    database_session,
)
from ac_race_engineer.domain.session import (
    SessionConditions,
    SessionMetadata,
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.events import (
    LapEvent,
    SectorEvent,
)
from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)

SESSION_ID = "demo-ac-magione-001"

CAR_ID = "ks_mazda_mx5_cup"
TRACK_ID = "magione"


LAPS = {
    1: (
        105000,
        (
            34000,
            38000,
            33000,
        ),
    ),
    2: (
        104000,
        (
            34000,
            37000,
            33000,
        ),
    ),
    3: (
        104500,
        (
            33700,
            37800,
            33000,
        ),
    ),
    4: (
        104300,
        (
            33400,
            38100,
            32800,
        ),
    ),
    5: (
        104154,
        (
            33769,
            37487,
            32898,
        ),
    ),
}


def main() -> int:
    engine = create_database_engine()

    started_at = datetime(
        2026,
        9,
        29,
        14,
        0,
        tzinfo=timezone.utc,
    )

    try:
        with database_session(
            engine
        ) as session:
            persistence = (
                AssettoCorsaPersistenceService(
                    session
                )
            )

            best_lap_time_ms = min(
                lap_time
                for (
                    lap_time,
                    _,
                ) in LAPS.values()
            )

            elapsed_seconds = 0.0

            for (
                lap_number,
                (
                    lap_time_ms,
                    sector_times,
                ),
            ) in LAPS.items():
                for (
                    sector_index,
                    sector_time_ms,
                ) in enumerate(
                    sector_times
                ):
                    elapsed_seconds += (
                        sector_time_ms
                        / 1000.0
                    )

                    timestamp = (
                        started_at
                        + timedelta(
                            seconds=(
                                elapsed_seconds
                            )
                        )
                    )

                    sector_event = (
                        SectorEvent(
                            timestamp=timestamp,
                            session_id=SESSION_ID,
                            car_id=CAR_ID,
                            track_id=TRACK_ID,
                            session_type=(
                                SessionType.PRACTICE
                            ),
                            lap_number=(
                                lap_number
                            ),
                            completed_laps=(
                                lap_number - 1
                            ),
                            sector_index=(
                                sector_index
                            ),
                            sector_number=(
                                sector_index + 1
                            ),
                            sector_time_ms=(
                                sector_time_ms
                            ),
                            position=1,
                            is_in_pit=False,
                            is_in_pit_lane=False,
                        )
                    )

                    persistence.save_sector_event(
                        sector_event
                    )

                lap_timestamp = (
                    started_at
                    + timedelta(
                        seconds=elapsed_seconds
                    )
                )

                lap_event = LapEvent(
                    timestamp=lap_timestamp,
                    session_id=SESSION_ID,
                    car_id=CAR_ID,
                    track_id=TRACK_ID,
                    session_type=(
                        SessionType.PRACTICE
                    ),
                    lap_number=(
                        lap_number
                    ),
                    lap_time_ms=(
                        lap_time_ms
                    ),
                    best_lap_time_ms=(
                        best_lap_time_ms
                    ),
                    is_best=(
                        lap_time_ms
                        == best_lap_time_ms
                    ),
                    position=1,
                    is_in_pit=False,
                    is_in_pit_lane=False,
                )

                persistence.save_lap_event(
                    lap_event
                )

            ended_at = (
                started_at
                + timedelta(
                    seconds=elapsed_seconds
                )
            )

            metadata = SessionMetadata(
                session_id=SESSION_ID,
                car_id=CAR_ID,
                track_id=TRACK_ID,
                source="assetto_corsa",
                session_type=(
                    SessionType.PRACTICE
                ),
                started_at=started_at,
                ended_at=ended_at,
                sample_count=10000,
                duration_seconds=(
                    elapsed_seconds
                ),
                initial_conditions=(
                    SessionConditions(
                        air_temperature_c=24.0,
                        track_temperature_c=31.0,
                        grip_level=0.97,
                    )
                ),
                final_conditions=(
                    SessionConditions(
                        air_temperature_c=25.0,
                        track_temperature_c=33.0,
                        grip_level=0.98,
                    )
                ),
            )

            persistence.save_completed_session(
                metadata
            )

        print()
        print(
            "Assetto Corsa demo session created."
        )

        print(
            f"Session ID: {SESSION_ID}"
        )

        print(
            f"Laps: {len(LAPS)}"
        )

        print(
            "Best lap: Lap 2 - 1:44.000"
        )

        print()

    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )