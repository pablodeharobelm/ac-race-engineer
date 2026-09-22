import pyarrow.parquet as pq

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
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


def test_bronze_ingestion_writes_parquet(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    ingestor = (
        BronzeTelemetryIngestor(
            output_directory=(
                tmp_path
                / "bronze"
                / "telemetry"
            )
        )
    )

    result = ingestor.ingest(
        raw_file
    )

    assert result.status == "written"

    assert result.row_count == 100

    table = pq.read_table(
        result.output_file
    )

    assert table.num_rows == 100

    assert (
        "vehicle_speed_kmh"
        in table.column_names
    )

    assert (
        "fl_pressure_psi"
        in table.column_names
    )


def test_bronze_contains_session_metadata(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    ingestor = (
        BronzeTelemetryIngestor(
            output_directory=(
                tmp_path
                / "bronze"
            )
        )
    )

    result = ingestor.ingest(
        raw_file
    )

    table = pq.read_table(
        result.output_file
    )

    row = table.to_pylist()[0]

    assert (
        row["setup_id"]
        == "setup-123"
    )

    assert (
        row["session_type"]
        == "test"
    )

    assert (
        row["telemetry_source"]
        == "simulator"
    )

    assert (
        row["schema_version"]
        == 1
    )


def test_bronze_ingestion_is_idempotent(
    tmp_path,
):

    raw_file = create_raw_session(
        tmp_path
    )

    ingestor = (
        BronzeTelemetryIngestor(
            output_directory=(
                tmp_path
                / "bronze"
            )
        )
    )

    first = ingestor.ingest(
        raw_file
    )

    second = ingestor.ingest(
        raw_file
    )

    assert first.status == "written"

    assert second.status == "skipped"

    assert (
        first.output_file
        == second.output_file
    )

    assert second.row_count == 100