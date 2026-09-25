from abc import ABC, abstractmethod

from ac_race_engineer.telemetry.models import TelemetryFrame


class TelemetrySource(ABC):
    """
    Base interface for any telemetry source.

    Implementations may obtain telemetry from:
    - a simulator,
    - a recorded session,
    - Assetto Corsa shared memory.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_frame(self) -> TelemetryFrame:
        """
        Return the next available telemetry frame.
        """
        raise NotImplementedError

