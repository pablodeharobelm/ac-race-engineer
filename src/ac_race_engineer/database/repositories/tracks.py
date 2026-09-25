from sqlalchemy import select
from sqlalchemy.orm import Session

from ac_race_engineer.database.models import TrackRecord


class TrackRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        track_id: int,
    ) -> TrackRecord | None:
        return self._session.get(
            TrackRecord,
            track_id,
        )

    def get_by_key(
        self,
        track_key: str,
    ) -> TrackRecord | None:
        statement = select(
            TrackRecord
        ).where(
            TrackRecord.track_key == track_key
        )

        return self._session.scalar(
            statement
        )

    def list_all(
        self,
    ) -> list[TrackRecord]:
        statement = select(
            TrackRecord
        ).order_by(
            TrackRecord.id
        )

        return list(
            self._session.scalars(
                statement
            )
        )

    def save(
        self,
        *,
        track_key: str,
        name: str,
        layout: str | None = None,
        length_m: float | None = None,
        metadata: dict | None = None,
    ) -> TrackRecord:
        record = self.get_by_key(
            track_key
        )

        if record is None:
            record = TrackRecord(
                track_key=track_key,
                name=name,
                layout=layout,
                length_m=length_m,
                metadata_json=metadata,
            )

            self._session.add(
                record
            )

        else:
            record.name = name
            record.layout = layout
            record.length_m = length_m
            record.metadata_json = metadata

        self._session.flush()

        return record

    def delete(
        self,
        record: TrackRecord,
    ) -> None:
        self._session.delete(
            record
        )

        self._session.flush()

