"""Bounded, reconnecting live snapshots for a local driving display."""
from dataclasses import dataclass
from math import isfinite
from time import monotonic

from ac_race_engineer.telemetry.assetto_corsa.exceptions import AssettoCorsaSharedMemoryError


@dataclass(frozen=True)
class LiveReading:
    state: str
    physics: object | None = None
    graphics: object | None = None
    static: object | None = None


class LiveMonitor:
    def __init__(self, factory, *, clock=monotonic, stale_seconds=2.0, retry_seconds=2.0):
        self.factory = factory
        self.clock = clock
        self.stale_seconds = stale_seconds
        self.retry_seconds = retry_seconds
        self.backend = None
        self.packet = None
        self.changed_at = 0.0
        self.retry_at = 0.0
        self.connected_once = False

    def close(self):
        if self.backend is not None:
            self.backend.close()
        self.backend = None
        self.packet = None

    def poll(self) -> LiveReading:
        now = self.clock()
        if self.backend is None:
            if now < self.retry_at:
                return LiveReading("disconnected" if self.connected_once else "waiting")
            try:
                self.backend = self.factory()
                self.changed_at = now
            except (AssettoCorsaSharedMemoryError, OSError):
                self.retry_at = now + self.retry_seconds
                return LiveReading("disconnected" if self.connected_once else "waiting")
        try:
            physics = self.backend.read_physics()
            graphics = self.backend.read_graphics()
            static = self.backend.read_static()
            if graphics.status not in (0, 1, 2, 3):
                raise ValueError("Unknown game status")
            if graphics.status == 0:
                self.close()
                self.retry_at = now + self.retry_seconds
                return LiveReading("waiting")
            if physics.packet_id != self.packet:
                self.packet = physics.packet_id
                self.changed_at = now
            elif graphics.status == 3:
                self.changed_at = now
            elif now - self.changed_at > self.stale_seconds:
                self.close()
                self.retry_at = now + self.retry_seconds
                return LiveReading("disconnected")
            if not all(isfinite(value) for value in (physics.speed_kmh, physics.gas, physics.brake, physics.clutch, graphics.normalized_car_position)):
                raise ValueError("Invalid telemetry")
            self.connected_once = True
            return LiveReading("paused" if graphics.status == 3 else "replay" if graphics.status == 1 else "live", physics, graphics, static)
        except (AssettoCorsaSharedMemoryError, OSError, ValueError):
            self.close()
            self.retry_at = now + self.retry_seconds
            return LiveReading("disconnected")
