from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import CarRecord


class CarRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        car_id: int,
    ) -> CarRecord | None:
        return self._session.get(
            CarRecord,
            car_id,
        )

    def get_by_key(
        self,
        car_key: str,
    ) -> CarRecord | None:
        statement = select(
            CarRecord
        ).where(
            CarRecord.car_key == car_key
        )

        return self._session.scalar(
            statement
        )

    def list_all(self) -> list[CarRecord]:
        statement = select(
            CarRecord
        ).order_by(
            CarRecord.id
        )

        return list(
            self._session.scalars(
                statement
            )
        )

    def save(
        self,
        *,
        car_key: str,
        name: str,
        manufacturer: str | None = None,
        drivetrain: str | None = None,
        metadata: dict | None = None,
    ) -> CarRecord:
        record = self.get_by_key(
            car_key
        )

        if record is None:
            record = CarRecord(
                car_key=car_key,
                name=name,
                manufacturer=manufacturer,
                drivetrain=drivetrain,
                metadata_json=metadata,
            )

            self._session.add(
                record
            )

        else:
            record.name = name
            record.manufacturer = manufacturer
            record.drivetrain = drivetrain
            record.metadata_json = metadata

        self._session.flush()

        return record

    def delete(
        self,
        record: CarRecord,
    ) -> None:
        self._session.delete(
            record
        )

        self._session.flush()

