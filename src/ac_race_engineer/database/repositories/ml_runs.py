from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import MLRunRecord


class MLRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        run_id: str,
    ) -> MLRunRecord | None:
        return self._session.get(
            MLRunRecord,
            run_id,
        )

    def list_for_experiment(
        self,
        experiment_id: str,
    ) -> list[MLRunRecord]:
        statement = (
            select(MLRunRecord)
            .where(
                MLRunRecord.experiment_id
                == experiment_id
            )
            .order_by(
                MLRunRecord.created_at
            )
        )

        return list(
            self._session.scalars(statement)
        )

    def save(
        self,
        *,
        run_id: str,
        model_type: str,
        target: str,
        experiment_id: str | None = None,
        features: list | None = None,
        metrics: dict | None = None,
        artifact_path: str | None = None,
    ) -> MLRunRecord:
        record = self.get_by_id(
            run_id
        )

        if record is None:
            record = MLRunRecord(
                id=run_id,
                experiment_id=experiment_id,
                model_type=model_type,
                target=target,
                features=features,
                metrics=metrics,
                artifact_path=artifact_path,
            )

            self._session.add(record)

        else:
            record.experiment_id = (
                experiment_id
            )
            record.model_type = model_type
            record.target = target
            record.features = features
            record.metrics = metrics
            record.artifact_path = (
                artifact_path
            )

        self._session.flush()

        return record

