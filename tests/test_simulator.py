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