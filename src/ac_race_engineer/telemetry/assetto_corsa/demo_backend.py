"""Repeatable two-lap driving scenario for exercising the real capture pipeline."""

from dataclasses import replace
from math import radians

from ac_race_engineer.telemetry.assetto_corsa.fake import FakeAssettoCorsaBackend
from ac_race_engineer.telemetry.assetto_corsa.snapshots import ACGraphicsSnapshot, ACPhysicsSnapshot
from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample


def _profile(progress: float, *, slower: bool) -> tuple[float, float, float, float]:
    speed, throttle, brake, steering = 160.0, 1.0, 0.0, 0.0
    for center in (0.35, 0.72):
        corner = max(0.0, 1.0 - abs(progress - center) / 0.11)
        speed -= 85.0 * corner
        steering += 22.0 * corner
        if center - 0.11 <= progress < center - 0.015:
            brake = max(brake, 0.85 * (center - 0.015 - progress) / 0.095)
            throttle = 0.0
        elif center - 0.015 <= progress <= center + 0.11:
            throttle = min(throttle, max(0.0, (progress - center) / 0.11))
    if slower and 0.24 <= progress <= 0.46:
        speed -= 9.0 * max(0.0, 1.0 - abs(progress - 0.35) / 0.11)
        if progress >= 0.35:
            throttle = min(throttle, max(0.0, (progress - 0.39) / 0.07))
    return speed, throttle, brake, steering


def build_demo_trace(*, slower: bool, points: int = 201, speed_factor: float = 1.0) -> tuple[DrivingTraceSample, ...]:
    if points < 20:
        raise ValueError("The driving demo needs at least 20 points per lap")
    samples = []
    elapsed = 0.0
    if not 0.8 <= speed_factor <= 1.2:
        raise ValueError("Demo speed factor must be between 0.8 and 1.2")
    previous_speed = 160.0 * speed_factor
    for index in range(points):
        progress = index / (points - 1)
        speed, throttle, brake, steering = _profile(progress, slower=slower)
        speed *= speed_factor
        if index:
            # Integrate traversal time for a synthetic 2.5 km track.
            elapsed += (2500.0 / (points - 1)) / ((speed + previous_speed) / 2 / 3.6)
        samples.append(DrivingTraceSample(progress, elapsed, speed, throttle, brake, steering))
        previous_speed = speed
    return tuple(samples)


class DemoAssettoCorsaBackend(FakeAssettoCorsaBackend):
    """One baseline lap, one slower lap, then a start/finish sample to close both."""

    def __init__(self, *, lap_count: int = 2) -> None:
        super().__init__()
        if not 2 <= lap_count <= 20:
            raise ValueError("Demo lap count must be between 2 and 20")
        self.laps = (build_demo_trace(slower=False), build_demo_trace(slower=True)) + tuple(
            build_demo_trace(slower=False, speed_factor=(1.015, 1.02, 1.018, 1.025)[index % 4])
            for index in range(lap_count - 2)
        )
        self.frames = [
            (lap_index, sample)
            for lap_index, lap in enumerate(self.laps)
            for sample in lap
        ] + [(lap_count, self.laps[0][0])]
        self._index = -1

    @property
    def sample_count(self) -> int:
        return len(self.frames)

    def read_physics(self) -> ACPhysicsSnapshot:
        original = super().read_physics()
        self._index = min(self._index + 1, self.sample_count - 1)
        _, sample = self.frames[self._index]
        return replace(
            original, gas=sample.throttle, brake=sample.brake,
            speed_kmh=sample.speed_kmh, steer_angle_rad=radians(sample.steering_angle_deg),
        )

    def read_graphics(self) -> ACGraphicsSnapshot:
        original = super().read_graphics()
        lap_index, sample = self.frames[max(0, self._index)]
        sector = min(2, int(sample.progress * 3))
        previous_lap = self.laps[max(0, min(len(self.laps) - 1, lap_index - 1))]
        current_lap = self.laps[min(len(self.laps) - 1, lap_index)]
        boundaries = [0] + [round((len(current_lap) - 1) * part / 3) for part in (1, 2, 3)]
        if sector == 0 and lap_index:
            last_sector_time = previous_lap[-1].elapsed_seconds - previous_lap[boundaries[2]].elapsed_seconds
        elif sector:
            last_sector_time = (
                current_lap[boundaries[sector]].elapsed_seconds
                - current_lap[boundaries[sector - 1]].elapsed_seconds
            )
        else:
            last_sector_time = 0.0
        return replace(
            original, completed_laps=lap_index, current_sector_index=sector,
            normalized_car_position=sample.progress,
            current_time_ms=round(sample.elapsed_seconds * 1000),
            last_time_ms=round(previous_lap[-1].elapsed_seconds * 1000) if lap_index else 0,
            best_time_ms=round(min(lap[-1].elapsed_seconds for lap in self.laps[:lap_index]) * 1000) if lap_index else 0,
            last_sector_time_ms=round(last_sector_time * 1000),
            distance_traveled_m=(lap_index + sample.progress) * 2500,
        )
