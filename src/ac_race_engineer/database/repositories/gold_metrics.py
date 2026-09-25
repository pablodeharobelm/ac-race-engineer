from sqlalchemy.orm import Session

from ac_race_engineer.database.models import (
    GoldSessionMetricsRecord,
)


class GoldSessionMetricsRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get_for_session(
        self,
        session_id: str,
    ) -> GoldSessionMetricsRecord | None:
        return self._session.get(
            GoldSessionMetricsRecord,
            session_id,
        )

    def save(
        self,
        *,
        session_id: str,
        metrics: dict,
        row_count: int | None = None,
        duration_seconds: float | None = None,
        pipeline_version: str | None = None,
    ) -> GoldSessionMetricsRecord:
        record = self.get_for_session(
            session_id
        )

        if record is None:
            record = (
                GoldSessionMetricsRecord(
                    session_id=session_id,
                    row_count=row_count,
                    duration_seconds=(
                        duration_seconds
                    ),
                    metrics=metrics,
                    pipeline_version=(
                        pipeline_version
                    ),
                )
            )

            self._session.add(record)

        else:
            record.row_count = row_count
            record.duration_seconds = (
                duration_seconds
            )
            record.metrics = metrics
            record.pipeline_version = (
                pipeline_version
            )

        self._session.flush()

        return record

