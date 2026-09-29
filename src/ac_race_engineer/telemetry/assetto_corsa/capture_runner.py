import time
from collections.abc import Callable
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)


@dataclass(frozen=True)
class CaptureStatistics:
    frames_read: int

    sessions_saved: int
    laps_saved: int
    sectors_saved: int


class AssettoCorsaCaptureRunner:
    """
    Coordinate Assetto Corsa telemetry capture and persistence.

    Responsibilities:
    - read TelemetryFrame objects,
    - drain generated session/lap/sector events,
    - persist those events,
    - close the current session cleanly when capture ends.
    """

    def __init__(
        self,
        *,
        source: AssettoCorsaSource,
        persistence: AssettoCorsaPersistenceService,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.persistence = persistence
        self._sleep = sleep

    def _drain_events(
        self,
    ) -> tuple[
        int,
        int,
        int,
    ]:
        result = (
            self.persistence.drain_source(
                self.source
            )
        )

        return (
            result.sessions_saved,
            result.laps_saved,
            result.sectors_saved,
        )

    def finish(
        self,
    ) -> tuple[
        int,
        int,
        int,
    ]:
        self.source.finish_current_session()

        return self._drain_events()

    def run(
        self,
        *,
        samples: int | None = None,
        interval_seconds: float = 0.05,
        on_frame: (
            Callable[
                [TelemetryFrame],
                None,
            ]
            | None
        ) = None,
    ) -> CaptureStatistics:
        if (
            samples is not None
            and samples <= 0
        ):
            raise ValueError(
                "samples must be greater "
                "than 0 or None"
            )

        if interval_seconds < 0.0:
            raise ValueError(
                "interval_seconds must be "
                "greater than or equal to 0"
            )

        frames_read = 0

        sessions_saved = 0
        laps_saved = 0
        sectors_saved = 0

        while (
            samples is None
            or frames_read < samples
        ):
            frame = (
                self.source.read_frame()
            )

            frames_read += 1

            if on_frame is not None:
                on_frame(
                    frame
                )

            (
                new_sessions,
                new_laps,
                new_sectors,
            ) = self._drain_events()

            sessions_saved += (
                new_sessions
            )

            laps_saved += (
                new_laps
            )

            sectors_saved += (
                new_sectors
            )

            if (
                interval_seconds > 0.0
                and (
                    samples is None
                    or frames_read < samples
                )
            ):
                self._sleep(
                    interval_seconds
                )

        (
            final_sessions,
            final_laps,
            final_sectors,
        ) = self.finish()

        sessions_saved += (
            final_sessions
        )

        laps_saved += (
            final_laps
        )

        sectors_saved += (
            final_sectors
        )

        return CaptureStatistics(
            frames_read=frames_read,
            sessions_saved=(
                sessions_saved
            ),
            laps_saved=laps_saved,
            sectors_saved=(
                sectors_saved
            ),
        )