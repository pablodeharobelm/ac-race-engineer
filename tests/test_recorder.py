from ac_race_engineer.storage.recorder import SessionRecorder
from ac_race_engineer.telemetry.simulator import SimulatorSource


def test_recorder_creates_session_file(tmp_path):

    simulator = SimulatorSource(
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    output_file = recorder.record_samples(
        sample_count=10,
    )

    assert output_file.exists()

    lines = output_file.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 10


def test_recorder_rejects_invalid_sample_count(tmp_path):

    simulator = SimulatorSource()

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    try:
        recorder.record_samples(
            sample_count=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )