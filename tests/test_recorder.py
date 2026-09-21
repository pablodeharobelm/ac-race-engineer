from ac_race_engineer.domain.session import (
    SessionMetadata,
    SessionType,
)
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
def test_recorder_creates_session_metadata(
    tmp_path,
):

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    telemetry_file = (
        recorder.record_samples(
            sample_count=100,
            session_type=(
                SessionType.TEST
            ),
            setup_id="setup-123",
        )
    )

    metadata_file = (
        telemetry_file.with_suffix(
            ".metadata.json"
        )
    )

    assert metadata_file.exists()

    metadata = (
        SessionMetadata
        .model_validate_json(
            metadata_file.read_text(
                encoding="utf-8"
            )
        )
    )

    assert (
        metadata.session_id
        == simulator.session_id
    )

    assert (
        metadata.car_id
        == "mazda_mx5_cup"
    )

    assert (
        metadata.track_id
        == "development_track"
    )

    assert (
        metadata.setup_id
        == "setup-123"
    )

    assert (
        metadata.source
        == "simulator"
    )

    assert (
        metadata.session_type
        == SessionType.TEST
    )

    assert (
        metadata.sample_count
        == 100
    )

    assert (
        metadata.duration_seconds
        > 0
    )


def test_metadata_records_conditions(
    tmp_path,
):

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    telemetry_file = (
        recorder.record_samples(
            sample_count=20,
        )
    )

    metadata_file = (
        telemetry_file.with_suffix(
            ".metadata.json"
        )
    )

    metadata = (
        SessionMetadata
        .model_validate_json(
            metadata_file.read_text(
                encoding="utf-8"
            )
        )
    )

    assert (
        metadata
        .initial_conditions
        .air_temperature_c
        == 24.0
    )

    assert (
        metadata
        .initial_conditions
        .track_temperature_c
        == 33.0
    )

    assert (
        0
        <= metadata.initial_conditions.grip_level
        <= 1
    )