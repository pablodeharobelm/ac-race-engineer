from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import (
    LapTraceRecord,
)


class LapTraceRepository:
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
    ) -> LapTraceRecord | None:
        statement = select(
            LapTraceRecord
        ).where(
            LapTraceRecord.session_id
            == session_id,
            LapTraceRecord.lap_number
            == lap_number,
        )

        return self._session.scalar(
            statement
        )

    def list_for_session(
        self,
        session_id: str,
    ) -> list[LapTraceRecord]:
        statement = (
            select(
                LapTraceRecord
            )
            .where(
                LapTraceRecord.session_id
                == session_id
            )
            .order_by(
                LapTraceRecord.lap_number
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
        sample_count: int,
        progress_start: float,
        progress_end: float,
        parquet_path: str,
        schema_version: int,
    ) -> LapTraceRecord:
        record = self.get(
            session_id=session_id,
            lap_number=lap_number,
        )

        if record is None:
            record = LapTraceRecord(
                session_id=session_id,
                lap_number=lap_number,
                lap_time_ms=lap_time_ms,
                sample_count=sample_count,
                progress_start=progress_start,
                progress_end=progress_end,
                parquet_path=parquet_path,
                schema_version=schema_version,
            )

            self._session.add(
                record
            )

        else:
            record.lap_time_ms = (
                lap_time_ms
            )

            record.sample_count = (
                sample_count
            )

            record.progress_start = (
                progress_start
            )

            record.progress_end = (
                progress_end
            )

            record.parquet_path = (
                parquet_path
            )

            record.schema_version = (
                schema_version
            )

        self._session.flush()

        return record