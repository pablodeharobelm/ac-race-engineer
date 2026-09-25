from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import SetupRecord


class SetupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        setup_id: int,
    ) -> SetupRecord | None:
        return self._session.get(
            SetupRecord,
            setup_id,
        )

    def get_by_key(
        self,
        setup_key: str,
    ) -> SetupRecord | None:
        statement = select(
            SetupRecord
        ).where(
            SetupRecord.setup_key == setup_key
        )

        return self._session.scalar(
            statement
        )

    def list_for_car(
        self,
        car_id: int,
    ) -> list[SetupRecord]:
        statement = (
            select(
                SetupRecord
            )
            .where(
                SetupRecord.car_id
                == car_id
            )
            .order_by(
                SetupRecord.id
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
        setup_key: str,
        car_id: int,
        name: str,
        parameters: dict,
    ) -> SetupRecord:
        record = self.get_by_key(
            setup_key
        )

        if record is None:
            record = SetupRecord(
                setup_key=setup_key,
                car_id=car_id,
                name=name,
                parameters=parameters,
            )

            self._session.add(
                record
            )

        else:
            record.car_id = car_id
            record.name = name
            record.parameters = parameters

        self._session.flush()

        return record

    def delete(
        self,
        record: SetupRecord,
    ) -> None:
        self._session.delete(
            record
        )

        self._session.flush()

