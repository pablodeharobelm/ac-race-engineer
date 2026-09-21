import pytest

from ac_race_engineer.analysis.dynamics_analyzer import (
    VehicleDynamicsAnalyzer,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_dynamics_analyzer_processes_session(
    tmp_path,
):

    simulator = SimulatorSource(
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    session_file = recorder.record_samples(
        sample_count=500,
    )

    analyzer = VehicleDynamicsAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    assert report.sample_count == 500

    assert report.cornering_sample_count > 0

    assert report.maximum_lateral_g > 0

    assert (
        report.maximum_absolute_steering_deg
        > 0
    )

    assert (
        report.average_front_slip_angle_deg
        >= 0
    )

    assert (
        report.average_rear_slip_angle_deg
        >= 0
    )


def test_dynamics_balance_percentages_sum_to_100(
    tmp_path,
):

    simulator = SimulatorSource(
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    session_file = recorder.record_samples(
        sample_count=500,
    )

    analyzer = VehicleDynamicsAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    total_percentage = (
        report.front_limited_percentage
        + report.rear_limited_percentage
        + report.neutral_balance_percentage
    )

    assert total_percentage == pytest.approx(
        100.0
    )


def test_dynamics_analyzer_rejects_invalid_threshold():

    with pytest.raises(
        ValueError,
        match="balance_threshold_deg",
    ):
        VehicleDynamicsAnalyzer(
            balance_threshold_deg=-1
        )