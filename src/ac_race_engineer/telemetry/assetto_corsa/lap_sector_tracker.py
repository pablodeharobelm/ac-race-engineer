from datetime import datetime

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.events import (
    LapEvent,
    SectorEvent,
)
from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
)


class AssettoCorsaLapSectorTracker:
    """
    Detect completed laps and sectors from consecutive
    Assetto Corsa graphics snapshots.
    """

    def __init__(
        self,
    ) -> None:
        self._previous: (
            ACGraphicsSnapshot | None
        ) = None

    def reset(
        self,
    ) -> None:
        self._previous = None

    def update(
        self,
        *,
        graphics: ACGraphicsSnapshot,
        timestamp: datetime,
        session_id: str,
        car_id: str,
        track_id: str,
        session_type: SessionType,
    ) -> tuple[
        LapEvent | None,
        SectorEvent | None,
    ]:
        previous = self._previous

        self._previous = graphics

        if previous is None:
            return (
                None,
                None,
            )

        lap_event = self._build_lap_event(
            previous=previous,
            current=graphics,
            timestamp=timestamp,
            session_id=session_id,
            car_id=car_id,
            track_id=track_id,
            session_type=session_type,
        )

        sector_event = (
            self._build_sector_event(
                previous=previous,
                current=graphics,
                timestamp=timestamp,
                session_id=session_id,
                car_id=car_id,
                track_id=track_id,
                session_type=session_type,
            )
        )

        return (
            lap_event,
            sector_event,
        )

    @staticmethod
    def _build_lap_event(
        *,
        previous: ACGraphicsSnapshot,
        current: ACGraphicsSnapshot,
        timestamp: datetime,
        session_id: str,
        car_id: str,
        track_id: str,
        session_type: SessionType,
    ) -> LapEvent | None:
        if (
            current.completed_laps
            <= previous.completed_laps
        ):
            return None

        lap_time_ms = max(
            0,
            current.last_time_ms,
        )

        best_lap_time_ms = max(
            0,
            current.best_time_ms,
        )

        is_best = (
            lap_time_ms > 0
            and best_lap_time_ms > 0
            and lap_time_ms
            <= best_lap_time_ms
        )

        return LapEvent(
            timestamp=timestamp,
            session_id=session_id,
            car_id=car_id,
            track_id=track_id,
            session_type=session_type,
            lap_number=(
                current.completed_laps
            ),
            lap_time_ms=lap_time_ms,
            best_lap_time_ms=(
                best_lap_time_ms
            ),
            is_best=is_best,
            position=current.position,
            is_in_pit=current.is_in_pit,
            is_in_pit_lane=(
                current.is_in_pit_lane
            ),
        )

    @staticmethod
    def _build_sector_event(
        *,
        previous: ACGraphicsSnapshot,
        current: ACGraphicsSnapshot,
        timestamp: datetime,
        session_id: str,
        car_id: str,
        track_id: str,
        session_type: SessionType,
    ) -> SectorEvent | None:
        if (
            current.current_sector_index
            == previous.current_sector_index
        ):
            return None

        completed_sector_index = max(
            0,
            previous.current_sector_index,
        )

        if (
            current.completed_laps
            > previous.completed_laps
        ):
            lap_number = max(
                1,
                current.completed_laps,
            )
        else:
            lap_number = (
                max(
                    0,
                    current.completed_laps,
                )
                + 1
            )

        return SectorEvent(
            timestamp=timestamp,
            session_id=session_id,
            car_id=car_id,
            track_id=track_id,
            session_type=session_type,
            lap_number=lap_number,
            completed_laps=max(
                0,
                current.completed_laps,
            ),
            sector_index=(
                completed_sector_index
            ),
            sector_number=(
                completed_sector_index + 1
            ),
            sector_time_ms=max(
                0,
                current.last_sector_time_ms,
            ),
            position=current.position,
            is_in_pit=current.is_in_pit,
            is_in_pit_lane=(
                current.is_in_pit_lane
            ),
        )