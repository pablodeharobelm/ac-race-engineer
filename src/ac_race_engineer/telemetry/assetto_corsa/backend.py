from abc import ABC, abstractmethod

from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
    ACPhysicsSnapshot,
    ACStaticSnapshot,
)


class AssettoCorsaBackend(ABC):
    """
    Low-level access to Assetto Corsa telemetry.

    Implementations can obtain data from:
    - Windows shared memory,
    - fake data for tests,
    - replayed snapshots.
    """

    @abstractmethod
    def read_physics(
        self,
    ) -> ACPhysicsSnapshot:
        raise NotImplementedError

    @abstractmethod
    def read_graphics(
        self,
    ) -> ACGraphicsSnapshot:
        raise NotImplementedError

    @abstractmethod
    def read_static(
        self,
    ) -> ACStaticSnapshot:
        raise NotImplementedError