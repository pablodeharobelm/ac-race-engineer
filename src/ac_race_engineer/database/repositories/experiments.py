from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import ExperimentRecord


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        experiment_id: str,
    ) -> ExperimentRecord | None:
        return self._session.get(
            ExperimentRecord,
            experiment_id,
        )

    def list_for_car(
        self,
        car_id: int,
    ) -> list[ExperimentRecord]:
        statement = (
            select(ExperimentRecord)
            .where(
                ExperimentRecord.car_id
                == car_id
            )
            .order_by(
                ExperimentRecord.created_at
            )
        )

        return list(
            self._session.scalars(statement)
        )

    def save(
        self,
        *,
        experiment_id: str,
        name: str,
        car_id: int,
        track_id: int | None = None,
        baseline_setup_id: int | None = None,
        status: str = "created",
        config: dict | None = None,
    ) -> ExperimentRecord:
        record = self.get_by_id(
            experiment_id
        )

        if record is None:
            record = ExperimentRecord(
                id=experiment_id,
                name=name,
                car_id=car_id,
                track_id=track_id,
                baseline_setup_id=baseline_setup_id,
                status=status,
                config=config,
            )

            self._session.add(record)

        else:
            record.name = name
            record.car_id = car_id
            record.track_id = track_id
            record.baseline_setup_id = (
                baseline_setup_id
            )
            record.status = status
            record.config = config

        self._session.flush()

        return record

