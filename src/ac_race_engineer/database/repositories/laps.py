from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import (
    LapRecord,
)


class LapRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get(
        self,
        *,
        session_id: str,
        lap_number: int,
    ) -> LapRecord | None:
        statement = select(
            LapRecord
        ).where(
            LapRecord.session_id
            == session_id,
            LapRecord.lap_number
            == lap_number,
        )

        return self._session.scalar(
            statement
        )

    def list_for_session(
        self,
        session_id: str,
    ) -> list[LapRecord]:
        statement = (
            select(
                LapRecord
            )
            .where(
                LapRecord.session_id
                == session_id
            )
            .order_by(
                LapRecord.lap_number
            )
        )

        return list(
            self._session.scalars(
                statement
            )
        )

    def save(
        self,
        *,
        session_id: str,
        lap_number: int,
        lap_time_ms: int,
        best_lap_time_ms: int,
        is_best: bool,
        position: int,
        is_in_pit: bool,
        is_in_pit_lane: bool,
        occurred_at: datetime,
    ) -> LapRecord:
        record = self.get(
            session_id=session_id,
            lap_number=lap_number,
        )

        if record is None:
            record = LapRecord(
                session_id=session_id,
                lap_number=lap_number,
                lap_time_ms=lap_time_ms,
                best_lap_time_ms=(
                    best_lap_time_ms
                ),
                is_best=is_best,
                position=position,
                is_in_pit=is_in_pit,
                is_in_pit_lane=(
                    is_in_pit_lane
                ),
                occurred_at=occurred_at,
            )

            self._session.add(
                record
            )

        else:
            record.lap_time_ms = (
                lap_time_ms
            )

            record.best_lap_time_ms = (
                best_lap_time_ms
            )

            record.is_best = is_best
            record.position = position
            record.is_in_pit = is_in_pit

            record.is_in_pit_lane = (
                is_in_pit_lane
            )

            record.occurred_at = (
                occurred_at
            )

        self._session.flush()

        return record