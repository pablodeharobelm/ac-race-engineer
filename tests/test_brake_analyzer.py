import pytest

from ac_race_engineer.analysis.brake_analyzer import (
    BrakeAnalyzer,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_brake_analyzer_processes_session(tmp_path):

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

    analyzer = BrakeAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    assert report.sample_count == 500

    assert len(report.wheels) == 4

    assert report.maximum_brake_input > 0

    assert report.braking_event_count > 0

    assert (
        report.average_brake_input_during_events
        > 0
    )

    assert (
        report.average_braking_event_duration_seconds
        > 0
    )


def test_brake_analyzer_calculates_temperatures(
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

    analyzer = BrakeAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    fl = report.wheels["FL"]

    assert fl.average_temperature_c > 0

    assert (
        fl.peak_temperature_c
        >= fl.average_temperature_c
    )


def test_brake_analyzer_rejects_invalid_threshold():

    with pytest.raises(
        ValueError,
        match="brake_threshold",
    ):
        BrakeAnalyzer(
            brake_threshold=1.5
        )