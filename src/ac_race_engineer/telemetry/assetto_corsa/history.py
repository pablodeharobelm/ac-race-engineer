from dataclasses import dataclass
from statistics import fmean, pstdev

from sqlalchemy.orm import Session

from ac_race_engineer.database.repositories.cars import (
    CarRepository,
)
from ac_race_engineer.database.repositories.laps import (
    LapRepository,
)
from ac_race_engineer.database.repositories.sectors import (
    SectorRepository,
)
from ac_race_engineer.database.repositories.sessions import (
    SessionRepository,
)
from ac_race_engineer.database.repositories.tracks import (
    TrackRepository,
)


@dataclass(frozen=True)
class SectorHistory:
    sector_number: int
    sector_time_ms: int


@dataclass(frozen=True)
class LapHistory:
    lap_number: int
    lap_time_ms: int

    is_session_best: bool

    position: int

    sectors: tuple[
        SectorHistory,
        ...,
    ]


@dataclass(frozen=True)
class SessionPerformanceSummary:
    session_id: str

    car_key: str
    track_key: str

    session_type: str
    source: str

    lap_count: int

    best_lap_number: int | None
    best_lap_time_ms: int | None

    average_lap_time_ms: float | None
    consistency_stddev_ms: float | None

    theoretical_best_lap_ms: int | None
    potential_gain_ms: int | None

    best_sectors: tuple[
        SectorHistory,
        ...,
    ]

    laps: tuple[
        LapHistory,
        ...,
    ]


class AssettoCorsaHistoryService:
    """
    Read persisted Assetto Corsa sessions and calculate
    basic performance statistics.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session_repository = (
            SessionRepository(
                session
            )
        )

        self.car_repository = (
            CarRepository(
                session
            )
        )

        self.track_repository = (
            TrackRepository(
                session
            )
        )

        self.lap_repository = (
            LapRepository(
                session
            )
        )

        self.sector_repository = (
            SectorRepository(
                session
            )
        )

    def get_summary(
        self,
        session_id: str,
    ) -> SessionPerformanceSummary:
        session_record = (
            self.session_repository.get_by_id(
                session_id
            )
        )

        if session_record is None:
            raise ValueError(
                "Session not found: "
                f"{session_id}"
            )

        car = (
            self.car_repository.get_by_id(
                session_record.car_id
            )
        )

        if car is None:
            raise ValueError(
                "Car not found for session: "
                f"{session_id}"
            )

        track_key = "unknown"

        if session_record.track_id is not None:
            track = (
                self.track_repository.get_by_id(
                    session_record.track_id
                )
            )

            if track is not None:
                track_key = (
                    track.track_key
                )

        lap_records = (
            self.lap_repository.list_for_session(
                session_id
            )
        )

        sector_records = (
            self.sector_repository.list_for_session(
                session_id
            )
        )

        valid_laps = [
            lap
            for lap in lap_records
            if lap.lap_time_ms > 0
        ]

        best_lap = None

        if valid_laps:
            best_lap = min(
                valid_laps,
                key=lambda lap: (
                    lap.lap_time_ms
                ),
            )

        average_lap_time_ms = None
        consistency_stddev_ms = None

        if valid_laps:
            times = [
                lap.lap_time_ms
                for lap in valid_laps
            ]

            average_lap_time_ms = (
                fmean(
                    times
                )
            )

            consistency_stddev_ms = (
                pstdev(
                    times
                )
            )

        best_sector_records: dict[
            int,
            object,
        ] = {}

        for sector in sector_records:
            if sector.sector_time_ms <= 0:
                continue

            current_best = (
                best_sector_records.get(
                    sector.sector_number
                )
            )

            if (
                current_best is None
                or sector.sector_time_ms
                < current_best.sector_time_ms
            ):
                best_sector_records[
                    sector.sector_number
                ] = sector

        best_sectors = tuple(
            SectorHistory(
                sector_number=(
                    sector_number
                ),
                sector_time_ms=(
                    record.sector_time_ms
                ),
            )
            for (
                sector_number,
                record,
            ) in sorted(
                best_sector_records.items()
            )
        )

        theoretical_best_lap_ms = None

        if best_sectors:
            theoretical_best_lap_ms = sum(
                sector.sector_time_ms
                for sector in best_sectors
            )

        potential_gain_ms = None

        if (
            best_lap is not None
            and theoretical_best_lap_ms
            is not None
        ):
            potential_gain_ms = max(
                0,
                best_lap.lap_time_ms
                - theoretical_best_lap_ms,
            )

        sectors_by_lap: dict[
            int,
            list[SectorHistory],
        ] = {}

        for sector in sector_records:
            sectors_by_lap.setdefault(
                sector.lap_number,
                [],
            ).append(
                SectorHistory(
                    sector_number=(
                        sector.sector_number
                    ),
                    sector_time_ms=(
                        sector.sector_time_ms
                    ),
                )
            )

        laps: list[
            LapHistory
        ] = []

        for lap in lap_records:
            sectors = tuple(
                sorted(
                    sectors_by_lap.get(
                        lap.lap_number,
                        [],
                    ),
                    key=lambda sector: (
                        sector.sector_number
                    ),
                )
            )

            laps.append(
                LapHistory(
                    lap_number=(
                        lap.lap_number
                    ),
                    lap_time_ms=(
                        lap.lap_time_ms
                    ),
                    is_session_best=(
                        best_lap is not None
                        and lap.id
                        == best_lap.id
                    ),
                    position=(
                        lap.position
                    ),
                    sectors=sectors,
                )
            )

        return SessionPerformanceSummary(
            session_id=(
                session_record.id
            ),
            car_key=(
                car.car_key
            ),
            track_key=track_key,
            session_type=(
                session_record.session_type
            ),
            source=(
                session_record.source
            ),
            lap_count=len(
                lap_records
            ),
            best_lap_number=(
                best_lap.lap_number
                if best_lap is not None
                else None
            ),
            best_lap_time_ms=(
                best_lap.lap_time_ms
                if best_lap is not None
                else None
            ),
            average_lap_time_ms=(
                average_lap_time_ms
            ),
            consistency_stddev_ms=(
                consistency_stddev_ms
            ),
            theoretical_best_lap_ms=(
                theoretical_best_lap_ms
            ),
            potential_gain_ms=(
                potential_gain_ms
            ),
            best_sectors=(
                best_sectors
            ),
            laps=tuple(
                laps
            ),
        )

def format_time_ms(
    milliseconds: float | None,
) -> str:
    if milliseconds is None:
        return "--:--.---"

    total_ms = round(
        milliseconds
    )

    minutes = (
        total_ms // 60000
    )

    remaining = (
        total_ms % 60000
    )

    seconds = (
        remaining // 1000
    )

    millis = (
        remaining % 1000
    )

    return (
        f"{minutes}:"
        f"{seconds:02d}."
        f"{millis:03d}"
    )