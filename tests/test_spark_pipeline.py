from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from ac_race_engineer.domain.session import SessionType
from ac_race_engineer.lakehouse.pipeline import LakehousePipeline
from ac_race_engineer.spark.pipeline import (
    SparkLakehousePipeline,
    SparkLakehousePipelineError,
)
from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.storage.recorder import SessionRecorder
from ac_race_engineer.telemetry.simulator import SimulatorSource


@pytest.fixture(scope="module")
def spark():
    session = create_spark_session(app_name="spark-pipeline-tests", master="local[2]")
    yield session
    session.stop()


def test_pipeline_end_to_end_parity_and_rerun(tmp_path, spark):
    raw = SessionRecorder(
        source=SimulatorSource(hz=20, seed=42), output_directory=tmp_path / "raw"
    ).record_samples(sample_count=30, session_type=SessionType.TEST, setup_id="pipeline")
    pipeline = SparkLakehousePipeline(
        spark, tmp_path / "bronze", tmp_path / "silver", tmp_path / "gold"
    )
    result = pipeline.run(raw)
    assert result.status == "completed"
    assert result.session_id == result.bronze.session_id == result.silver.session_id
    assert result.session_id == result.gold.session_id
    assert result.gold.source_rows == 30
    assert result.gold.output_rows == 1
    assert [stage.status for stage in result.stages] == ["written"] * 3
    assert result.started_at <= result.completed_at
    assert result.duration_seconds >= 0
    assert result.stages[0].input_path == str(raw)
    for previous, current in zip(result.stages, result.stages[1:]):
        assert previous.output_path == current.input_path
        assert previous.completed_at <= current.started_at
    for stage in result.stages:
        assert stage.duration_seconds >= 0
        assert stage.started_at <= stage.completed_at
        assert Path(stage.output_path).exists()
    assert type(result).model_validate_json(result.model_dump_json()) == result

    pandas_result = LakehousePipeline(
        tmp_path / "bronze", tmp_path / "pandas_silver", tmp_path / "pandas_gold"
    ).run(raw)
    pandas_row = pd.read_parquet(pandas_result.gold.output_file).iloc[0]
    spark_row = spark.read.parquet(result.gold.output_path).first().asDict()
    assert set(pandas_row.index) == set(spark_row)
    for column, value in spark_row.items():
        if column == "gold_processed_at":
            continue
        if column in {"started_at", "ended_at"}:
            # PySpark collects naive datetimes in the local Windows timezone.
            assert pd.Timestamp(value.astimezone()).tz_convert("UTC") == pandas_row[column]
        elif isinstance(value, (float, int)):
            assert value == pytest.approx(pandas_row[column], abs=1e-6)
        else:
            assert value == pandas_row[column]

    repeated = pipeline.run(raw)
    assert [stage.status for stage in repeated.stages] == ["skipped"] * 3
    assert repeated.gold.source_checksum == result.gold.source_checksum
    assert repeated.gold.output_path == result.gold.output_path
    assert spark.range(1).count() == 1  # The caller still owns the session.


@pytest.mark.parametrize("failed_stage", ["bronze", "silver", "gold"])
def test_pipeline_failure_retains_progress_and_can_retry(tmp_path, failed_stage):
    # Isolate orchestration: actual transforms are covered by the integration test.
    pipeline = SparkLakehousePipeline(
        Mock(), tmp_path / "bronze", tmp_path / "silver", tmp_path / "gold"
    )
    from ac_race_engineer.domain.lakehouse import (
        BronzeIngestionResult,
        SparkGoldAggregationResult,
        SparkSilverProcessingResult,
    )

    common = {
        "session_id": "session",
        "status": "written",
        "partition_date": "2026-09-23",
        "car_id": "car",
        "track_id": "track",
    }
    bronze = BronzeIngestionResult(**common, row_count=3, output_file="bronze.parquet")
    silver = SparkSilverProcessingResult(
        **common,
        input_rows=3,
        output_rows=3,
        duplicate_rows_removed=0,
        quarantined_rows=0,
        output_path="silver",
        quarantine_path=None,
        manifest_file="silver.json",
        source_checksum="abc",
        spark_version="4.2.0",
    )
    gold = SparkGoldAggregationResult(
        **common,
        source_rows=3,
        output_rows=1,
        output_path="gold",
        manifest_file="gold.json",
        source_checksum="def",
        spark_version="4.2.0",
    )
    methods = {
        "bronze": Mock(return_value=bronze),
        "silver": Mock(return_value=silver),
        "gold": Mock(return_value=gold),
    }
    pipeline.bronze.ingest = methods["bronze"]
    pipeline.silver.process = methods["silver"]
    pipeline.gold.aggregate = methods["gold"]
    failure = ValueError("invalid source")
    methods[failed_stage].side_effect = failure
    with pytest.raises(SparkLakehousePipelineError) as caught:
        pipeline.run("raw.jsonl")
    assert caught.value.__cause__ is failure
    report = caught.value.result
    assert report.status == "failed"
    assert report.stages[-1].stage == failed_stage
    assert report.stages[-1].status == "failed"
    assert "invalid source" in report.stages[-1].error
    assert len(report.stages) == list(methods).index(failed_stage) + 1
    for later in list(methods)[len(report.stages) :]:
        methods[later].assert_not_called()
    methods[failed_stage].side_effect = None
    assert pipeline.run("raw.jsonl").status == "completed"

    methods["silver"].return_value = silver.model_copy(update={"session_id": "other"})
    methods["gold"].reset_mock()
    with pytest.raises(SparkLakehousePipelineError, match="different session IDs") as mismatch:
        pipeline.run("raw.jsonl")
    assert mismatch.value.result.stages[-1].stage == "silver"
    methods["gold"].assert_not_called()


def test_pipeline_missing_raw_reports_bronze_failure(tmp_path):
    pipeline = SparkLakehousePipeline(
        Mock(), tmp_path / "bronze", tmp_path / "silver", tmp_path / "gold"
    )
    with pytest.raises(SparkLakehousePipelineError) as caught:
        pipeline.run(tmp_path / "missing.jsonl")
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert caught.value.result.bronze is None
    assert caught.value.result.stages[0].stage == "bronze"
