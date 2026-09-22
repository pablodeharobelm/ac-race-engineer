import pandas as pd

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)
from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def create_bronze_session(
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

    raw_file = (
        recorder.record_samples(
            sample_count=100,
            session_type=(
                SessionType.TEST
            ),
            setup_id="setup-123",
        )
    )

    bronze = (
        BronzeTelemetryIngestor(
            output_directory=(
                tmp_path
                / "bronze"
                / "telemetry"
            )
        )
    )

    result = bronze.ingest(
        raw_file
    )

    return result.output_file


def test_silver_creates_enriched_dataset(
    tmp_path,
):

    bronze_file = (
        create_bronze_session(
            tmp_path
        )
    )

    processor = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path / "silver"
            )
        )
    )

    result = processor.process(
        bronze_file
    )

    assert result.status == "written"
    assert result.input_rows == 100
    assert result.output_rows == 100

    dataframe = pd.read_parquet(
        result.output_file
    )

    assert (
        "vehicle_speed_mps"
        in dataframe.columns
    )

    assert (
        "front_pressure_psi"
        in dataframe.columns
    )

    assert (
        "front_rear_slip_delta_deg"
        in dataframe.columns
    )

    assert (
        dataframe[
            "is_valid"
        ].all()
    )


def test_silver_removes_duplicates(
    tmp_path,
):

    bronze_file = (
        create_bronze_session(
            tmp_path
        )
    )

    dataframe = pd.read_parquet(
        bronze_file
    )

    duplicate = (
        dataframe.iloc[
            [0]
        ]
        .copy()
    )

    dataframe = pd.concat(
        [
            dataframe,
            duplicate,
        ],
        ignore_index=True,
    )

    dataframe.to_parquet(
        bronze_file,
        index=False,
    )

    processor = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path / "silver"
            )
        )
    )

    result = processor.process(
        bronze_file
    )

    assert result.input_rows == 101

    assert (
        result.duplicate_rows_removed
        == 1
    )

    assert result.output_rows == 100


def test_silver_quarantines_invalid_rows(
    tmp_path,
):

    bronze_file = (
        create_bronze_session(
            tmp_path
        )
    )

    dataframe = pd.read_parquet(
        bronze_file
    )

    dataframe.loc[
        0,
        "vehicle_throttle",
    ] = 1.5

    dataframe.to_parquet(
        bronze_file,
        index=False,
    )

    processor = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path / "silver"
            )
        )
    )

    result = processor.process(
        bronze_file
    )

    assert result.output_rows == 99

    assert (
        result.quarantined_rows
        == 1
    )

    assert (
        result.quarantine_file
        is not None
    )

    quarantine = pd.read_parquet(
        result.quarantine_file
    )

    assert len(quarantine) == 1

    assert not bool(
        quarantine.iloc[0][
            "is_valid"
        ]
    )


def test_silver_is_idempotent(
    tmp_path,
):

    bronze_file = (
        create_bronze_session(
            tmp_path
        )
    )

    processor = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path / "silver"
            )
        )
    )

    first = processor.process(
        bronze_file
    )

    second = processor.process(
        bronze_file
    )

    assert first.status == "written"
    assert second.status == "skipped"

    assert (
        first.source_checksum
        == second.source_checksum
    )

    assert (
        first.output_file
        == second.output_file
    )