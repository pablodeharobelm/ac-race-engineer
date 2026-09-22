import pandas as pd

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)
from ac_race_engineer.lakehouse.gold import (
    GoldSessionAggregator,
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


def create_silver_session(
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

    bronze_result = bronze.ingest(
        raw_file
    )

    silver = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path / "silver"
            )
        )
    )

    silver_result = silver.process(
        bronze_result.output_file
    )

    return silver_result.output_file


def test_gold_creates_one_row_per_session(
    tmp_path,
):

    silver_file = (
        create_silver_session(
            tmp_path
        )
    )

    aggregator = (
        GoldSessionAggregator(
            output_directory=(
                tmp_path / "gold"
            )
        )
    )

    result = aggregator.aggregate(
        silver_file
    )

    assert result.status == "written"

    assert result.source_rows == 100

    assert result.output_rows == 1

    dataframe = pd.read_parquet(
        result.output_file
    )

    assert len(dataframe) == 1


def test_gold_contains_session_metrics(
    tmp_path,
):

    silver_file = (
        create_silver_session(
            tmp_path
        )
    )

    aggregator = (
        GoldSessionAggregator(
            output_directory=(
                tmp_path / "gold"
            )
        )
    )

    result = aggregator.aggregate(
        silver_file
    )

    dataframe = pd.read_parquet(
        result.output_file
    )

    row = dataframe.iloc[0]

    assert (
        row["setup_id"]
        == "setup-123"
    )

    assert (
        row["maximum_speed_kmh"]
        > 0
    )

    assert (
        row["average_front_pressure_psi"]
        > 0
    )

    assert (
        row["average_front_core_temp_c"]
        > 0
    )

    assert (
        row["average_front_slip_angle_deg"]
        >= 0
    )

    assert (
        row["valid_row_percentage"]
        == 100.0
    )


def test_gold_calculates_fuel_usage(
    tmp_path,
):

    silver_file = (
        create_silver_session(
            tmp_path
        )
    )

    aggregator = (
        GoldSessionAggregator(
            output_directory=(
                tmp_path / "gold"
            )
        )
    )

    result = aggregator.aggregate(
        silver_file
    )

    dataframe = pd.read_parquet(
        result.output_file
    )

    fuel_used = dataframe.iloc[0][
        "fuel_used_l"
    ]

    assert fuel_used >= 0


def test_gold_is_idempotent(
    tmp_path,
):

    silver_file = (
        create_silver_session(
            tmp_path
        )
    )

    aggregator = (
        GoldSessionAggregator(
            output_directory=(
                tmp_path / "gold"
            )
        )
    )

    first = aggregator.aggregate(
        silver_file
    )

    second = aggregator.aggregate(
        silver_file
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