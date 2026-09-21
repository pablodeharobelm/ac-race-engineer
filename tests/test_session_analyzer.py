import pytest

from ac_race_engineer.analysis.session_analyzer import (
    SessionAnalyzer,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_analyzer_processes_session(tmp_path):

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

    analyzer = SessionAnalyzer()

    summary = analyzer.analyze(
        session_file=session_file,
    )

    assert summary.sample_count == 100

    assert summary.duration_seconds > 0

    assert summary.maximum_speed_kmh > 0

    assert summary.maximum_lateral_g >= 0

    assert summary.maximum_braking_g >= 0

    assert len(summary.wheels) == 4

    assert "FL" in summary.wheels
    assert "FR" in summary.wheels
    assert "RL" in summary.wheels
    assert "RR" in summary.wheels


def test_analyzer_rejects_empty_session(tmp_path):

    empty_file = (
        tmp_path
        / "empty_session.jsonl"
    )

    empty_file.write_text(
        "",
        encoding="utf-8",
    )

    analyzer = SessionAnalyzer()

    with pytest.raises(
        ValueError,
        match="no telemetry frames",
    ):
        analyzer.analyze(
            session_file=empty_file,
        )