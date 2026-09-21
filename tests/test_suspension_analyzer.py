import pytest

from ac_race_engineer.analysis.suspension_analyzer import (
    SuspensionAnalyzer,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_suspension_analyzer_processes_session(
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

    analyzer = SuspensionAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    assert report.sample_count == 500

    assert len(report.wheels) == 4

    assert report.average_front_travel_mm > 0
    assert report.average_rear_travel_mm > 0

    assert report.average_left_load_n > 0
    assert report.average_right_load_n > 0

    assert report.total_bottoming_events >= 0


def test_suspension_analyzer_calculates_wheel_data(
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
        sample_count=200,
    )

    analyzer = SuspensionAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    fl = report.wheels["FL"]

    assert fl.average_travel_mm > 0
    assert fl.maximum_travel_mm >= fl.average_travel_mm

    assert fl.average_load_n > 0
    assert fl.maximum_load_n >= fl.minimum_load_n


def test_suspension_analyzer_rejects_invalid_threshold():

    with pytest.raises(
        ValueError,
        match="bottoming_threshold_mm",
    ):
        SuspensionAnalyzer(
            bottoming_threshold_mm=0
        )