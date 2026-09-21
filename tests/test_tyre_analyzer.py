import pytest

from ac_race_engineer.analysis.tyre_analyzer import (
    TyreAnalyzer,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_tyre_analyzer_processes_session(tmp_path):

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

    analyzer = TyreAnalyzer()

    report = analyzer.analyze(
        session_file=session_file,
    )

    assert report.sample_count == 200

    assert len(report.wheels) == 4

    fl = report.wheels["FL"]

    assert fl.average_pressure_psi > 0

    assert fl.average_core_temp_c > 0

    assert fl.peak_core_temp_c >= (
        fl.average_core_temp_c
    )

    assert fl.thermal_spread_c >= 0


def test_tyre_analyzer_detects_temperature_gradient(
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
        sample_count=100,
    )

    analyzer = TyreAnalyzer()

    report = analyzer.analyze(
        session_file
    )

    fl = report.wheels["FL"]

    assert fl.average_inner_temp_c > (
        fl.average_outer_temp_c
    )

    assert fl.inner_outer_delta_c > 0


def test_tyre_analyzer_rejects_invalid_window():

    with pytest.raises(
        ValueError,
        match="window_size",
    ):
        TyreAnalyzer(
            window_size=0
        )