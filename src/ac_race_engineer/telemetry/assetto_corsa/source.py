from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from ac_race_engineer.domain.session import (
    SessionConditions,
    SessionMetadata,
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.backend import (
    AssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.events import (
    LapEvent,
    SectorEvent,
)
from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaStaleDataError,
)
from ac_race_engineer.telemetry.assetto_corsa.lap_sector_tracker import (
    AssettoCorsaLapSectorTracker,
)
from ac_race_engineer.telemetry.assetto_corsa.mapper import (
    map_assetto_corsa_frame,
)
from ac_race_engineer.telemetry.assetto_corsa.session_tracker import (
    AssettoCorsaSessionTracker,
    AssettoCorsaSessionUpdate,
)
from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)
from ac_race_engineer.telemetry.source import (
    TelemetrySource,
)


class AssettoCorsaSource(
    TelemetrySource
):
    """
    High-level Assetto Corsa telemetry source.

    Responsibilities:
    - read raw Assetto Corsa snapshots,
    - detect stale telemetry,
    - detect session changes,
    - manage session identifiers,
    - manage sample indexes,
    - create SessionMetadata,
    - detect completed laps,
    - detect completed sectors,
    - convert AC telemetry into TelemetryFrame.
    """

    def __init__(
        self,
        backend: AssettoCorsaBackend,
        *,
        stale_timeout_seconds: float | None = 2.0,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        if (
            stale_timeout_seconds is not None
            and stale_timeout_seconds <= 0.0
        ):
            raise ValueError(
                "stale_timeout_seconds must be "
                "greater than 0 or None"
            )

        self.backend = backend

        self.stale_timeout_seconds = (
            stale_timeout_seconds
        )

        self._clock = clock

        self.session_tracker = (
            AssettoCorsaSessionTracker()
        )

        self.lap_sector_tracker = (
            AssettoCorsaLapSectorTracker()
        )

        self.session_id = str(
            uuid4()
        )

        self.sample_index = 0

        self._started_at = (
            self._clock()
        )

        self._last_physics_packet_id: (
            int | None
        ) = None

        self._last_packet_change_at = (
            self._started_at
        )

        self._last_session_update: (
            AssettoCorsaSessionUpdate | None
        ) = None

        self._current_session_type: (
            SessionType | None
        ) = None

        self._current_session_first_frame: (
            TelemetryFrame | None
        ) = None

        self._current_session_last_frame: (
            TelemetryFrame | None
        ) = None

        self._completed_sessions: deque[
            SessionMetadata
        ] = deque()

        self._last_completed_session: (
            SessionMetadata | None
        ) = None

        self._lap_events: deque[
            LapEvent
        ] = deque()

        self._sector_events: deque[
            SectorEvent
        ] = deque()

        self._last_lap_event: (
            LapEvent | None
        ) = None

        self._last_sector_event: (
            SectorEvent | None
        ) = None

    @property
    def source_name(
        self,
    ) -> str:
        return "assetto_corsa"

    @property
    def last_session_update(
        self,
    ) -> AssettoCorsaSessionUpdate | None:
        return self._last_session_update

    @property
    def last_completed_session(
        self,
    ) -> SessionMetadata | None:
        return self._last_completed_session

    @property
    def completed_sessions_pending(
        self,
    ) -> int:
        return len(
            self._completed_sessions
        )

    @property
    def last_lap_event(
        self,
    ) -> LapEvent | None:
        return self._last_lap_event

    @property
    def last_sector_event(
        self,
    ) -> SectorEvent | None:
        return self._last_sector_event

    @property
    def lap_events_pending(
        self,
    ) -> int:
        return len(
            self._lap_events
        )

    @property
    def sector_events_pending(
        self,
    ) -> int:
        return len(
            self._sector_events
        )

    @staticmethod
    def _conditions_from_frame(
        frame: TelemetryFrame,
    ) -> SessionConditions:
        return SessionConditions(
            air_temperature_c=(
                frame.environment.air_temperature_c
            ),
            track_temperature_c=(
                frame.environment.track_temperature_c
            ),
            grip_level=(
                frame.environment.grip_level
            ),
        )

    def _reset_stale_tracking(
        self,
        *,
        packet_id: int,
        now: float,
    ) -> None:
        self._last_physics_packet_id = (
            packet_id
        )

        self._last_packet_change_at = (
            now
        )

    def _start_new_session(
        self,
        *,
        session_type: SessionType,
        packet_id: int,
        now: float,
    ) -> None:
        self.session_id = str(
            uuid4()
        )

        self.sample_index = 0

        self._started_at = now

        self._current_session_type = (
            session_type
        )

        self._current_session_first_frame = (
            None
        )

        self._current_session_last_frame = (
            None
        )

        self.lap_sector_tracker.reset()

        self._reset_stale_tracking(
            packet_id=packet_id,
            now=now,
        )

    def _record_frame(
        self,
        frame: TelemetryFrame,
    ) -> None:
        if (
            self._current_session_first_frame
            is None
        ):
            self._current_session_first_frame = (
                frame
            )

        self._current_session_last_frame = (
            frame
        )

    def _record_lap_sector_events(
        self,
        *,
        frame: TelemetryFrame,
        graphics: ACGraphicsSnapshot,
    ) -> None:
        session_type = (
            self._current_session_type
            or SessionType.TEST
        )

        (
            lap_event,
            sector_event,
        ) = self.lap_sector_tracker.update(
            graphics=graphics,
            timestamp=frame.timestamp,
            session_id=frame.session_id,
            car_id=frame.car_id,
            track_id=frame.track_id,
            session_type=session_type,
        )

        if lap_event is not None:
            self._lap_events.append(
                lap_event
            )

            self._last_lap_event = (
                lap_event
            )

        if sector_event is not None:
            self._sector_events.append(
                sector_event
            )

            self._last_sector_event = (
                sector_event
            )

    def _complete_current_session(
        self,
    ) -> SessionMetadata | None:
        first_frame = (
            self._current_session_first_frame
        )

        last_frame = (
            self._current_session_last_frame
        )

        if (
            first_frame is None
            or last_frame is None
        ):
            return None

        metadata = SessionMetadata(
            session_id=(
                first_frame.session_id
            ),
            car_id=(
                first_frame.car_id
            ),
            track_id=(
                first_frame.track_id
            ),
            source=self.source_name,
            session_type=(
                self._current_session_type
                or SessionType.TEST
            ),
            started_at=(
                first_frame.timestamp
            ),
            ended_at=(
                last_frame.timestamp
            ),
            sample_count=(
                last_frame.sample_index
            ),
            duration_seconds=(
                last_frame.elapsed_seconds
            ),
            initial_conditions=(
                self._conditions_from_frame(
                    first_frame
                )
            ),
            final_conditions=(
                self._conditions_from_frame(
                    last_frame
                )
            ),
        )

        self._completed_sessions.append(
            metadata
        )

        self._last_completed_session = (
            metadata
        )

        self._current_session_type = None

        self._current_session_first_frame = (
            None
        )

        self._current_session_last_frame = (
            None
        )

        return metadata

    def pop_completed_session(
        self,
    ) -> SessionMetadata | None:
        if not self._completed_sessions:
            return None

        return self._completed_sessions.popleft()

    def pop_lap_event(
        self,
    ) -> LapEvent | None:
        if not self._lap_events:
            return None

        return self._lap_events.popleft()

    def pop_sector_event(
        self,
    ) -> SectorEvent | None:
        if not self._sector_events:
            return None

        return self._sector_events.popleft()

    def finish_current_session(
        self,
    ) -> SessionMetadata | None:
        """
        Explicitly finish the current Assetto Corsa session.

        Useful when:
        - the application closes,
        - telemetry capture is stopped,
        - Assetto Corsa disconnects intentionally.
        """

        metadata = (
            self._complete_current_session()
        )

        if metadata is None:
            return None

        self.session_tracker.reset()

        self.lap_sector_tracker.reset()

        self.sample_index = 0

        self._last_physics_packet_id = None

        self._last_packet_change_at = (
            self._clock()
        )

        return metadata

    def _check_stale_packet(
        self,
        *,
        packet_id: int,
        now: float,
    ) -> None:
        if (
            self._last_physics_packet_id
            is None
        ):
            self._reset_stale_tracking(
                packet_id=packet_id,
                now=now,
            )

            return

        if (
            packet_id
            != self._last_physics_packet_id
        ):
            self._reset_stale_tracking(
                packet_id=packet_id,
                now=now,
            )

            return

        if (
            self.stale_timeout_seconds
            is None
        ):
            return

        stale_for_seconds = (
            now
            - self._last_packet_change_at
        )

        if (
            stale_for_seconds
            >= self.stale_timeout_seconds
        ):
            raise AssettoCorsaStaleDataError(
                "Assetto Corsa physics telemetry "
                "has stopped updating for "
                f"{stale_for_seconds:.2f} seconds "
                f"(packet_id={packet_id})"
            )

    def read_frame(
        self,
    ) -> TelemetryFrame:
        physics = (
            self.backend.read_physics()
        )

        graphics = (
            self.backend.read_graphics()
        )

        static = (
            self.backend.read_static()
        )

        now = self._clock()

        session_update = (
            self.session_tracker.update(
                graphics,
                static,
            )
        )

        self._last_session_update = (
            session_update
        )

        if session_update.new_session:
            self._complete_current_session()

            self._start_new_session(
                session_type=(
                    session_update.session_type
                ),
                packet_id=(
                    physics.packet_id
                ),
                now=now,
            )

        else:
            self._check_stale_packet(
                packet_id=(
                    physics.packet_id
                ),
                now=now,
            )

        self.sample_index += 1

        elapsed_seconds = (
            now
            - self._started_at
        )

        frame = map_assetto_corsa_frame(
            physics=physics,
            graphics=graphics,
            static=static,
            timestamp=datetime.now(
                timezone.utc
            ),
            session_id=(
                self.session_id
            ),
            sample_index=(
                self.sample_index
            ),
            elapsed_seconds=(
                elapsed_seconds
            ),
        )

        self._record_frame(
            frame
        )

        self._record_lap_sector_events(
            frame=frame,
            graphics=graphics,
        )

        return frame