from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import SessionRecord


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        session_id: str,
    ) -> SessionRecord | None:
        return self._session.get(
            SessionRecord,
            session_id,
        )

    def list_for_car(
        self,
        car_id: int,
    ) -> list[SessionRecord]:
        statement = (
            select(SessionRecord)
            .where(
                SessionRecord.car_id == car_id
            )
            .order_by(
                SessionRecord.created_at
            )
        )

        return list(
            self._session.scalars(statement)
        )

    def save(
        self,
        *,
        session_id: str,
        car_id: int,
        session_type: str,
        track_id: int | None = None,
        setup_id: int | None = None,
        source: str = "simulator",
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        conditions: dict | None = None,
        raw_path: str | None = None,
        bronze_path: str | None = None,
        silver_path: str | None = None,
    ) -> SessionRecord:
        record = self.get_by_id(
            session_id
        )

        if record is None:
            record = SessionRecord(
                id=session_id,
                car_id=car_id,
                track_id=track_id,
                setup_id=setup_id,
                session_type=session_type,
                source=source,
                started_at=started_at,
                ended_at=ended_at,
                conditions=conditions,
                raw_path=raw_path,
                bronze_path=bronze_path,
                silver_path=silver_path,
            )

            self._session.add(record)

        else:
            record.car_id = car_id
            record.track_id = track_id
            record.setup_id = setup_id
            record.session_type = session_type
            record.source = source
            record.started_at = started_at
            record.ended_at = ended_at
            record.conditions = conditions
            record.raw_path = raw_path
            record.bronze_path = bronze_path
            record.silver_path = silver_path

        self._session.flush()

        return record