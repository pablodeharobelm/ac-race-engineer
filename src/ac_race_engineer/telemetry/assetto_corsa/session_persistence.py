from sqlalchemy.orm import Session

from ac_race_engineer.database.repositories.cars import (
    CarRepository,
)
from ac_race_engineer.database.repositories.sessions import (
    SessionRepository,
)
from ac_race_engineer.database.repositories.tracks import (
    TrackRepository,
)
from ac_race_engineer.domain.session import (
    SessionMetadata,
)


class AssettoCorsaSessionPersistenceService:
    """
    Persist completed Assetto Corsa sessions using the
    existing relational repository layer.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.car_repository = CarRepository(
            session
        )

        self.track_repository = TrackRepository(
            session
        )

        self.session_repository = (
            SessionRepository(
                session
            )
        )

    def save_session(
        self,
        metadata: SessionMetadata,
    ):
        car = (
            self.car_repository.get_by_key(
                metadata.car_id
            )
        )

        if car is None:
            car = self.car_repository.save(
                car_key=metadata.car_id,
                name=metadata.car_id,
            )

        track = (
            self.track_repository.get_by_key(
                metadata.track_id
            )
        )

        if track is None:
            track = self.track_repository.save(
                track_key=metadata.track_id,
                name=metadata.track_id,
            )

        conditions = {
            "initial": {
                "air_temperature_c": (
                    metadata.initial_conditions.air_temperature_c
                ),
                "track_temperature_c": (
                    metadata.initial_conditions.track_temperature_c
                ),
                "grip_level": (
                    metadata.initial_conditions.grip_level
                ),
            },
            "final": {
                "air_temperature_c": (
                    metadata.final_conditions.air_temperature_c
                ),
                "track_temperature_c": (
                    metadata.final_conditions.track_temperature_c
                ),
                "grip_level": (
                    metadata.final_conditions.grip_level
                ),
            },
        }

        return self.session_repository.save(
            session_id=metadata.session_id,
            car_id=car.id,
            track_id=track.id,
            session_type=str(
                metadata.session_type
            ),
            source=metadata.source,
            started_at=metadata.started_at,
            ended_at=metadata.ended_at,
            conditions=conditions,
        )