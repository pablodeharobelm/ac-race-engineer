from ac_race_engineer.telemetry.simulator import SimulatorSource


def test_simulator_generates_frame():

    simulator = SimulatorSource(
        hz=20,
    )

    frame = simulator.read_frame()

    assert frame.session_id
    assert frame.sample_index == 1
    assert frame.car_id == "mazda_mx5_cup"

    assert frame.vehicle.speed_kmh > 0

    assert len(frame.wheels) == 4

    assert "FL" in frame.wheels
    assert "FR" in frame.wheels
    assert "RL" in frame.wheels
    assert "RR" in frame.wheels


def test_simulator_advances_time():

    simulator = SimulatorSource(
        hz=20,
    )

    first = simulator.read_frame()
    second = simulator.read_frame()

    assert second.sample_index == 2
    assert second.elapsed_seconds > first.elapsed_seconds

def test_tyre_temperature_changes_over_time():

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    first_frame = simulator.read_frame()

    initial_temperature = (
        first_frame
        .wheels["FL"]
        .tyre_temp_core_c
    )

    final_frame = first_frame

    for _ in range(600):
        final_frame = (
            simulator.read_frame()
        )

    final_temperature = (
        final_frame
        .wheels["FL"]
        .tyre_temp_core_c
    )

    assert (
        final_temperature
        > initial_temperature
    )


def test_tyre_pressure_changes_with_temperature():

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    first_frame = simulator.read_frame()

    initial_pressure = (
        first_frame
        .wheels["FL"]
        .pressure_psi
    )

    final_frame = first_frame

    for _ in range(600):
        final_frame = (
            simulator.read_frame()
        )

    final_pressure = (
        final_frame
        .wheels["FL"]
        .pressure_psi
    )

    assert (
        final_pressure
        != initial_pressure
    )


def test_simulator_can_be_deterministic():

    simulator_a = SimulatorSource(
        hz=20,
        seed=42,
    )

    simulator_b = SimulatorSource(
        hz=20,
        seed=42,
    )

    frame_a = simulator_a.read_frame()
    frame_b = simulator_b.read_frame()

    assert (
        frame_a.vehicle.speed_kmh
        == frame_b.vehicle.speed_kmh
    )

    assert (
        frame_a.wheels["FL"].load_n
        == frame_b.wheels["FL"].load_n
    )