from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.services.experiment_service import (
    ExperimentService,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def create_session(
    tmp_path,
    seed: int,
):

    simulator = SimulatorSource(
        hz=20,
        seed=seed,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    return recorder.record_samples(
        sample_count=600,
    )


def test_compare_two_experiments(
    tmp_path,
):

    baseline_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
        },
    )

    candidate_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Higher front pressure",
        values={
            "front_pressure": 25.0,
            "rear_pressure": 24.5,
        },
    )

    baseline_session = create_session(
        tmp_path / "baseline",
        seed=42,
    )

    candidate_session = create_session(
        tmp_path / "candidate",
        seed=43,
    )

    service = ExperimentService()

    comparison = service.compare(
        baseline_setup=baseline_setup,
        candidate_setup=candidate_setup,
        baseline_session=baseline_session,
        candidate_session=candidate_session,
    )

    assert (
        comparison.car_id
        == "mazda_mx5_cup"
    )

    assert (
        comparison.track_id
        == "development_track"
    )

    assert len(
        comparison.setup_changes.changes
    ) == 1

    assert "FL" in comparison.tyres
    assert "FR" in comparison.tyres

    assert (
        comparison
        .dynamics
        .maximum_lateral_g
        .baseline
        > 0
    )


def test_setup_change_delta(
    tmp_path,
):

    baseline_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_pressure": 24.5,
        },
    )

    candidate_setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Candidate",
        values={
            "front_pressure": 25.0,
        },
    )

    baseline_session = create_session(
        tmp_path / "baseline",
        seed=42,
    )

    candidate_session = create_session(
        tmp_path / "candidate",
        seed=43,
    )

    service = ExperimentService()

    comparison = service.compare(
        baseline_setup=baseline_setup,
        candidate_setup=candidate_setup,
        baseline_session=baseline_session,
        candidate_session=candidate_session,
    )

    change = (
        comparison
        .setup_changes
        .changes[0]
    )

    assert change.parameter == "front_pressure"
    assert change.delta == 0.5