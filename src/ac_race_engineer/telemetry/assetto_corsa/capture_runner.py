import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.exceptions import AssettoCorsaSharedMemoryError
from ac_race_engineer.telemetry.assetto_corsa.persistence import AssettoCorsaPersistenceService
from ac_race_engineer.telemetry.assetto_corsa.source import AssettoCorsaSource
from ac_race_engineer.telemetry.models import TelemetryFrame


@dataclass(frozen=True)
class CaptureStatistics:
    frames_read: int
    sessions_saved: int
    laps_saved: int
    sectors_saved: int
    traces_saved: int


class AssettoCorsaCaptureRunner:
    """Coordinate capture, event persistence and clean session shutdown."""

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
        self.statistics = CaptureStatistics(0, 0, 0, 0, 0)

    def _drain_events(self) -> tuple[int, int, int, int]:
        result = self.persistence.drain_source(self.source)
        previous = self.statistics
        self.statistics = CaptureStatistics(
            previous.frames_read,
            previous.sessions_saved + result.sessions_saved,
            previous.laps_saved + result.laps_saved,
            previous.sectors_saved + result.sectors_saved,
            previous.traces_saved + result.traces_saved,
        )
        return (
            result.sessions_saved, result.laps_saved,
            result.sectors_saved, result.traces_saved,
        )

    def finish(self) -> tuple[int, int, int, int]:
        self.source.finish_current_session()
        return self._drain_events()

    def run(
        self,
        *,
        samples: int | None = None,
        interval_seconds: float = 0.05,
        on_frame: Callable[[TelemetryFrame], None] | None = None,
    ) -> CaptureStatistics:
        if samples is not None and samples <= 0:
            raise ValueError("samples must be greater than 0 or None")
        if not math.isfinite(interval_seconds) or interval_seconds < 0:
            raise ValueError("interval_seconds must be finite and greater than or equal to 0")

        self.statistics = CaptureStatistics(0, 0, 0, 0, 0)
        try:
            while samples is None or self.statistics.frames_read < samples:
                frame = self.source.read_frame()
                previous = self.statistics
                self.statistics = CaptureStatistics(
                    previous.frames_read + 1, previous.sessions_saved,
                    previous.laps_saved, previous.sectors_saved, previous.traces_saved,
                )
                self._drain_events()
                if on_frame is not None:
                    on_frame(frame)
                if interval_seconds > 0 and (
                    samples is None or self.statistics.frames_read < samples
                ):
                    self._sleep(interval_seconds)
        except (KeyboardInterrupt, AssettoCorsaSharedMemoryError):
            self.finish()
            raise

        self.finish()
        return self.statistics
