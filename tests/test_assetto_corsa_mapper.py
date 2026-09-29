from dataclasses import replace
from datetime import datetime, timezone
from math import degrees

import pytest

from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.mapper import (
    WHEEL_ORDER,
    map_assetto_corsa_frame,
    normalize_gear,
)


@pytest.mark.parametrize(
    ("raw_gear", "expected"),
    [
        (0, -1),
        (1, 0),
        (2, 1),
        (3, 2),
        (4, 3),
        (7, 6),
    ],
)
def test_normalize_gear(
    raw_gear: int,
    expected: int,
) -> None:
    assert normalize_gear(raw_gear) == expected


def test_maps_basic_vehicle_data() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()
    static = backend.read_static()

    timestamp = datetime.now(
        timezone.utc
    )

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=timestamp,
        session_id="test-session",
        sample_index=1,
        elapsed_seconds=2.5,
    )

    assert frame.timestamp == timestamp

    assert frame.session_id == (
        "test-session"
    )

    assert frame.sample_index == 1
    assert frame.elapsed_seconds == 2.5

    assert frame.car_id == (
        "ks_mazda_mx5_cup"
    )

    assert frame.track_id == "magione"

    assert frame.vehicle.speed_kmh == pytest.approx(
        143.2
    )

    assert frame.vehicle.rpm == 6150
    assert frame.vehicle.gear == 3

    assert frame.vehicle.throttle == pytest.approx(
        0.82
    )

    assert frame.vehicle.brake == pytest.approx(
        0.0
    )

    assert frame.vehicle.clutch == pytest.approx(
        0.0
    )

    assert (
        frame.vehicle.steering_angle_deg
        == pytest.approx(
            degrees(0.08)
        )
    )

    assert frame.vehicle.lateral_g == pytest.approx(
        0.72
    )

    assert (
        frame.vehicle.longitudinal_g
        == pytest.approx(0.18)
    )

    assert frame.vehicle.fuel_l == pytest.approx(
        32.4
    )

    assert (
        frame.vehicle.brake_bias
        == pytest.approx(0.64)
    )


def test_maps_environment() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()
    static = backend.read_static()

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=datetime.now(
            timezone.utc
        ),
        session_id="environment-test",
        sample_index=1,
        elapsed_seconds=0.0,
    )

    assert (
        frame.environment.air_temperature_c
        == pytest.approx(24.0)
    )

    assert (
        frame.environment.track_temperature_c
        == pytest.approx(31.0)
    )

    assert (
        frame.environment.grip_level
        == pytest.approx(0.98)
    )


def test_maps_four_wheels_in_correct_order() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()
    static = backend.read_static()

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=datetime.now(
            timezone.utc
        ),
        session_id="wheel-test",
        sample_index=1,
        elapsed_seconds=0.0,
    )

    assert tuple(frame.wheels) == WHEEL_ORDER

    assert (
        frame.wheels["FL"].pressure_psi
        == pytest.approx(26.1)
    )

    assert (
        frame.wheels["FR"].pressure_psi
        == pytest.approx(26.0)
    )

    assert (
        frame.wheels["RL"].pressure_psi
        == pytest.approx(25.8)
    )

    assert (
        frame.wheels["RR"].pressure_psi
        == pytest.approx(25.9)
    )


def test_converts_wheel_speed_to_kmh() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()
    static = backend.read_static()

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=datetime.now(
            timezone.utc
        ),
        session_id="speed-test",
        sample_index=1,
        elapsed_seconds=0.0,
    )

    expected_fl_speed = (
        112.0
        * 0.31
        * 3.6
    )

    assert (
        frame.wheels["FL"].wheel_speed_kmh
        == pytest.approx(
            expected_fl_speed
        )
    )


def test_converts_suspension_to_mm() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()
    static = backend.read_static()

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=datetime.now(
            timezone.utc
        ),
        session_id="suspension-test",
        sample_index=1,
        elapsed_seconds=0.0,
    )

    assert (
        frame.wheels[
            "FL"
        ].suspension_travel_mm
        == pytest.approx(52.0)
    )

    assert (
        frame.wheels[
            "RR"
        ].suspension_travel_mm
        == pytest.approx(48.0)
    )


def test_clamps_control_values() -> None:
    backend = FakeAssettoCorsaBackend()

    original = backend.read_physics()

    physics = replace(
        original,
        gas=1.5,
        brake=-0.2,
        clutch=2.0,
        fuel_l=-5.0,
        brake_bias=1.4,
    )

    graphics = replace(
        backend.read_graphics(),
        surface_grip=1.8,
    )

    static = backend.read_static()

    frame = map_assetto_corsa_frame(
        physics=physics,
        graphics=graphics,
        static=static,
        timestamp=datetime.now(
            timezone.utc
        ),
        session_id="clamp-test",
        sample_index=1,
        elapsed_seconds=0.0,
    )

    assert frame.vehicle.throttle == 1.0
    assert frame.vehicle.brake == 0.0
    assert frame.vehicle.clutch == 1.0

    assert frame.vehicle.fuel_l == 0.0
    assert frame.vehicle.brake_bias == 1.0

    assert frame.environment.grip_level == 1.0