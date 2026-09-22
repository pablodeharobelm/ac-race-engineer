from pathlib import Path

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.pipeline import (
    LakehousePipeline,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def create_raw_session(
    tmp_path,
):

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(
            tmp_path / "raw"
        ),
    )

    return recorder.record_samples(
        sample_count=100,
        session_type=SessionType.TEST,
        setup_id="setup-123",
    )


def create_pipeline(
    tmp_path,
):

    return LakehousePipeline(
        bronze_directory=(
            tmp_path
            / "bronze"
            / "telemetry"
        ),
        silver_directory=(
            tmp_path
            / "silver"
        ),
        gold_directory=(
            tmp_path
            / "gold"
        ),
    )


def test_pipeline_processes_raw_to_gold(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    pipeline = create_pipeline(
        tmp_path
    )

    result = pipeline.run(
        raw_file
    )

    assert result.status == "completed"

    assert (
        result.bronze.status
        == "written"
    )

    assert (
        result.silver.status
        == "written"
    )

    assert (
        result.gold.status
        == "written"
    )

    assert Path(
        result.bronze.output_file
    ).exists()

    assert Path(
        result.silver.output_file
    ).exists()

    assert Path(
        result.gold.output_file
    ).exists()


def test_pipeline_preserves_session_id(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    pipeline = create_pipeline(
        tmp_path
    )

    result = pipeline.run(
        raw_file
    )

    assert (
        result.session_id
        == result.bronze.session_id
        == result.silver.session_id
        == result.gold.session_id
    )


def test_pipeline_is_idempotent(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    pipeline = create_pipeline(
        tmp_path
    )

    first = pipeline.run(
        raw_file
    )

    second = pipeline.run(
        raw_file
    )

    assert (
        first.bronze.status
        == "written"
    )

    assert (
        first.silver.status
        == "written"
    )

    assert (
        first.gold.status
        == "written"
    )

    assert (
        second.bronze.status
        == "skipped"
    )

    assert (
        second.silver.status
        == "skipped"
    )

    assert (
        second.gold.status
        == "skipped"
    )


def test_pipeline_gold_has_one_row(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    pipeline = create_pipeline(
        tmp_path
    )

    result = pipeline.run(
        raw_file
    )

    assert (
        result.gold.output_rows
        == 1
    )