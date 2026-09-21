from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_front_pressure_affects_telemetry():

    baseline_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_pressure": 24.5,
        },
    )

    high_pressure_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="High pressure",
        values={
            "front_pressure": 26.0,
        },
    )

    baseline = SimulatorSource(
        seed=42,
        setup=baseline_setup,
    )

    candidate = SimulatorSource(
        seed=42,
        setup=high_pressure_setup,
    )

    baseline_frame = baseline.read_frame()
    candidate_frame = candidate.read_frame()

    assert (
        candidate_frame
        .wheels["FL"]
        .pressure_psi
        >
        baseline_frame
        .wheels["FL"]
        .pressure_psi
    )


def test_camber_affects_temperature_spread():

    baseline_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_camber": -2.0,
        },
    )

    aggressive_camber_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="More camber",
        values={
            "front_camber": -4.0,
        },
    )

    baseline = SimulatorSource(
        seed=42,
        setup=baseline_setup,
    )

    candidate = SimulatorSource(
        seed=42,
        setup=aggressive_camber_setup,
    )

    baseline_frame = baseline.read_frame()
    candidate_frame = candidate.read_frame()

    baseline_delta = (
        baseline_frame
        .wheels["FL"]
        .tyre_temp_inner_c
        -
        baseline_frame
        .wheels["FL"]
        .tyre_temp_outer_c
    )

    candidate_delta = (
        candidate_frame
        .wheels["FL"]
        .tyre_temp_inner_c
        -
        candidate_frame
        .wheels["FL"]
        .tyre_temp_outer_c
    )

    assert candidate_delta > baseline_delta


def test_brake_bias_affects_front_brake_temperature():

    rearward_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Rearward bias",
        values={
            "brake_bias": 0.55,
        },
    )

    forward_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Forward bias",
        values={
            "brake_bias": 0.70,
        },
    )

    rearward = SimulatorSource(
        seed=42,
        setup=rearward_setup,
    )

    forward = SimulatorSource(
        seed=42,
        setup=forward_setup,
    )

    rearward_frame = None
    forward_frame = None

    for _ in range(200):

        rearward_frame = (
            rearward.read_frame()
        )

        forward_frame = (
            forward.read_frame()
        )

    assert rearward_frame is not None
    assert forward_frame is not None

    assert (
        forward_frame
        .wheels["FL"]
        .brake_temp_c
        >
        rearward_frame
        .wheels["FL"]
        .brake_temp_c
    )


def test_simulator_rejects_setup_from_other_car():

    setup = CarSetup(
        car_id="other_car",
        name="Invalid",
        values={},
    )

    try:
        SimulatorSource(
            setup=setup
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Expected setup mismatch to fail"
        )