from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from pyspark.sql import SparkSession

from ac_race_engineer.domain.lakehouse import (
    SparkLakehousePipelineResult,
    SparkPipelineStageResult,
)
from ac_race_engineer.lakehouse.bronze import BronzeTelemetryIngestor
from ac_race_engineer.spark.gold import SparkGoldSessionAggregator
from ac_race_engineer.spark.silver import SparkSilverTelemetryProcessor


class SparkLakehousePipelineError(RuntimeError):
    """A failed run, including completed stages and the original exception as cause."""

    def __init__(self, result: SparkLakehousePipelineResult):
        self.result = result
        failed = result.stages[-1]
        super().__init__(f"Spark Lakehouse stage {failed.stage} failed: {failed.error}")


class SparkLakehousePipeline:
    """Run the existing Bronze ingestor followed by Spark Silver and Gold.

    The caller owns the Spark session. Re-running uses each stage's existing
    idempotency and manifests; a failure never hides the original exception.
    """

    def __init__(
        self,
        spark: SparkSession,
        bronze_directory: str | Path = "data/bronze/telemetry",
        silver_directory: str | Path = "data/silver_spark",
        gold_directory: str | Path = "data/gold_spark/session_summary",
    ):
        self.bronze = BronzeTelemetryIngestor(bronze_directory)
        self.silver = SparkSilverTelemetryProcessor(spark, silver_directory)
        self.gold = SparkGoldSessionAggregator(spark, gold_directory)

    def run(self, raw_file: str | Path) -> SparkLakehousePipelineResult:
        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        stages = []
        results = {}
        source = str(Path(raw_file))
        session_id = None

        for stage, process in (
            ("bronze", self.bronze.ingest),
            ("silver", self.silver.process),
            ("gold", self.gold.aggregate),
        ):
            stage_started_at = datetime.now(timezone.utc)
            stage_started = perf_counter()
            try:
                result = process(source)
                if session_id is not None and result.session_id != session_id:
                    raise ValueError("Lakehouse stages produced different session IDs")
                session_id = result.session_id
                output = result.output_file if stage == "bronze" else result.output_path
                rows = result.row_count if stage == "bronze" else result.output_rows
                stages.append(
                    SparkPipelineStageResult(
                        stage=stage,
                        status=result.status,
                        input_path=source,
                        output_path=output,
                        output_rows=rows,
                        started_at=stage_started_at,
                        completed_at=datetime.now(timezone.utc),
                        duration_seconds=perf_counter() - stage_started,
                    )
                )
                results[stage] = result
                source = output
            except Exception as exc:
                stages.append(
                    SparkPipelineStageResult(
                        stage=stage,
                        status="failed",
                        input_path=source,
                        started_at=stage_started_at,
                        completed_at=datetime.now(timezone.utc),
                        duration_seconds=perf_counter() - stage_started,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                report = SparkLakehousePipelineResult(
                    session_id=session_id,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    duration_seconds=perf_counter() - started,
                    stages=stages,
                    **results,
                )
                raise SparkLakehousePipelineError(report) from exc

        return SparkLakehousePipelineResult(
            session_id=session_id,
            status="completed",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            duration_seconds=perf_counter() - started,
            stages=stages,
            **results,
        )




