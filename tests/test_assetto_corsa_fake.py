from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)


def test_fake_physics_packet_increases() -> None:
    backend = FakeAssettoCorsaBackend()

    first = backend.read_physics()
    second = backend.read_physics()

    assert second.packet_id == (
        first.packet_id + 1
    )


def test_graphics_uses_current_packet() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()
    graphics = backend.read_graphics()

    assert (
        graphics.packet_id
        == physics.packet_id
    )


def test_fake_static_data() -> None:
    backend = FakeAssettoCorsaBackend()

    static = backend.read_static()

    assert static.car_model == (
        "ks_mazda_mx5_cup"
    )

    assert static.track == "magione"

    assert static.max_rpm == 7500
    assert static.max_fuel_l == 45.0

    assert static.tyre_radius_m == (
        0.31,
        0.31,
        0.31,
        0.31,
    )


def test_fake_wheel_data_has_four_values() -> None:
    backend = FakeAssettoCorsaBackend()

    physics = backend.read_physics()

    assert len(
        physics.wheel_pressure_psi
    ) == 4

    assert len(
        physics.wheel_load_n
    ) == 4

    assert len(
        physics.wheel_slip
    ) == 4

    assert len(
        physics.brake_temp_c
    ) == 4

    assert len(
        physics.suspension_travel_m
    ) == 4