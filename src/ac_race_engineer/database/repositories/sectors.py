from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import (
    SectorRecord,
)


class SectorRepository:
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
        sector_number: int,
    ) -> SectorRecord | None:
        statement = select(
            SectorRecord
        ).where(
            SectorRecord.session_id
            == session_id,
            SectorRecord.lap_number
            == lap_number,
            SectorRecord.sector_number
            == sector_number,
        )

        return self._session.scalar(
            statement
        )

    def list_for_session(
        self,
        session_id: str,
    ) -> list[SectorRecord]:
        statement = (
            select(
                SectorRecord
            )
            .where(
                SectorRecord.session_id
                == session_id
            )
            .order_by(
                SectorRecord.lap_number,
                SectorRecord.sector_number,
            )
        )

        return list(
            self._session.scalars(
                statement
            )
        )

    def list_for_lap(
        self,
        *,
        session_id: str,
        lap_number: int,
    ) -> list[SectorRecord]:
        statement = (
            select(
                SectorRecord
            )
            .where(
                SectorRecord.session_id
                == session_id,
                SectorRecord.lap_number
                == lap_number,
            )
            .order_by(
                SectorRecord.sector_number
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
        sector_index: int,
        sector_number: int,
        sector_time_ms: int,
        position: int,
        is_in_pit: bool,
        is_in_pit_lane: bool,
        occurred_at: datetime,
    ) -> SectorRecord:
        record = self.get(
            session_id=session_id,
            lap_number=lap_number,
            sector_number=sector_number,
        )

        if record is None:
            record = SectorRecord(
                session_id=session_id,
                lap_number=lap_number,
                sector_index=sector_index,
                sector_number=sector_number,
                sector_time_ms=sector_time_ms,
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
            record.sector_index = (
                sector_index
            )

            record.sector_time_ms = (
                sector_time_ms
            )

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