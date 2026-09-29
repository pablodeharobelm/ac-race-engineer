from dataclasses import dataclass
from enum import IntEnum

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
    ACStaticSnapshot,
)


class ACStatus(IntEnum):
    OFF = 0
    REPLAY = 1
    LIVE = 2
    PAUSE = 3


class ACSessionType(IntEnum):
    UNKNOWN = -1
    PRACTICE = 0
    QUALIFY = 1
    RACE = 2
    HOTLAP = 3
    TIME_ATTACK = 4
    DRIFT = 5
    DRAG = 6


@dataclass(frozen=True)
class AssettoCorsaSessionUpdate:
    new_session: bool

    lap_completed: bool
    sector_changed: bool

    ac_status: ACStatus

    ac_session_type: ACSessionType
    session_type: SessionType

    completed_laps: int
    current_sector_index: int

    current_time_ms: int
    last_time_ms: int
    best_time_ms: int

    last_sector_time_ms: int

    position: int

    is_in_pit: bool
    is_in_pit_lane: bool


def map_ac_session_type(
    session_type: int,
) -> SessionType:
    try:
        ac_session = ACSessionType(
            session_type
        )
    except ValueError:
        return SessionType.TEST

    mapping = {
        ACSessionType.PRACTICE: (
            SessionType.PRACTICE
        ),
        ACSessionType.QUALIFY: (
            SessionType.QUALIFYING
        ),
        ACSessionType.RACE: (
            SessionType.RACE
        ),
        ACSessionType.HOTLAP: (
            SessionType.HOTLAP
        ),
        ACSessionType.TIME_ATTACK: (
            SessionType.HOTLAP
        ),
        ACSessionType.DRIFT: (
            SessionType.TEST
        ),
        ACSessionType.DRAG: (
            SessionType.TEST
        ),
        ACSessionType.UNKNOWN: (
            SessionType.TEST
        ),
    }

    return mapping[
        ac_session
    ]


def parse_ac_status(
    status: int,
) -> ACStatus:
    try:
        return ACStatus(
            status
        )
    except ValueError:
        return ACStatus.OFF


def parse_ac_session_type(
    session_type: int,
) -> ACSessionType:
    try:
        return ACSessionType(
            session_type
        )
    except ValueError:
        return ACSessionType.UNKNOWN


class AssettoCorsaSessionTracker:
    """
    Detect Assetto Corsa session boundaries,
    completed laps and sector transitions.

    It is intentionally independent from the
    Windows shared-memory layer so it can be
    completely unit tested without the game.
    """

    def __init__(
        self,
    ) -> None:
        self._last_graphics: (
            ACGraphicsSnapshot | None
        ) = None

        self._last_static: (
            ACStaticSnapshot | None
        ) = None

    def reset(
        self,
    ) -> None:
        self._last_graphics = None
        self._last_static = None

    def _is_new_session(
        self,
        graphics: ACGraphicsSnapshot,
        static: ACStaticSnapshot,
    ) -> bool:
        previous_graphics = (
            self._last_graphics
        )

        previous_static = (
            self._last_static
        )

        if (
            previous_graphics is None
            or previous_static is None
        ):
            return True

        if (
            static.car_model
            != previous_static.car_model
        ):
            return True

        if (
            static.track
            != previous_static.track
        ):
            return True

        if (
            graphics.session_type
            != previous_graphics.session_type
        ):
            return True

        if (
            graphics.completed_laps
            < previous_graphics.completed_laps
        ):
            return True

        if (
            graphics.packet_id
            < previous_graphics.packet_id
        ):
            return True

        previous_status = parse_ac_status(
            previous_graphics.status
        )

        current_status = parse_ac_status(
            graphics.status
        )

        return (
            current_status == ACStatus.LIVE
            and previous_status
            in {
                ACStatus.OFF,
                ACStatus.REPLAY,
            }
        )

    def update(
        self,
        graphics: ACGraphicsSnapshot,
        static: ACStaticSnapshot,
    ) -> AssettoCorsaSessionUpdate:
        previous = (
            self._last_graphics
        )

        new_session = (
            self._is_new_session(
                graphics,
                static,
            )
        )

        lap_completed = False
        sector_changed = False

        if (
            previous is not None
            and not new_session
        ):
            lap_completed = (
                graphics.completed_laps
                > previous.completed_laps
            )

            sector_changed = (
                graphics.current_sector_index
                != previous.current_sector_index
            )

        update = (
            AssettoCorsaSessionUpdate(
                new_session=new_session,
                lap_completed=lap_completed,
                sector_changed=(
                    sector_changed
                ),
                ac_status=parse_ac_status(
                    graphics.status
                ),
                ac_session_type=(
                    parse_ac_session_type(
                        graphics.session_type
                    )
                ),
                session_type=(
                    map_ac_session_type(
                        graphics.session_type
                    )
                ),
                completed_laps=(
                    graphics.completed_laps
                ),
                current_sector_index=(
                    graphics.current_sector_index
                ),
                current_time_ms=(
                    graphics.current_time_ms
                ),
                last_time_ms=(
                    graphics.last_time_ms
                ),
                best_time_ms=(
                    graphics.best_time_ms
                ),
                last_sector_time_ms=(
                    graphics.last_sector_time_ms
                ),
                position=(
                    graphics.position
                ),
                is_in_pit=(
                    graphics.is_in_pit
                ),
                is_in_pit_lane=(
                    graphics.is_in_pit_lane
                ),
            )
        )

        self._last_graphics = graphics
        self._last_static = static

        return update