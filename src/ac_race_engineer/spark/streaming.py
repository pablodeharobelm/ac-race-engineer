"""File-backed Structured Streaming using the existing Bronze/Silver contract."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import StructType

from ac_race_engineer.spark.silver import SparkSilverTelemetryProcessor


@dataclass
class TelemetryStreamingQueries:
    """Queries owned by this run; the caller continues to own Spark itself."""

    queries: dict[str, StreamingQuery]

    def check(self) -> None:
        for stage, query in self.queries.items():
            failure = query.exception()
            if failure is not None:
                raise RuntimeError(f"Telemetry stream {stage} failed") from failure

    def drain(self) -> None:
        # Drain upstream before downstream. This does not force event-time windows closed.
        for query in self.queries.values():
            query.processAllAvailable()
        self.check()

    def stop(self) -> None:
        for query in reversed(list(self.queries.values())):
            if query.isActive:
                query.stop()


class SparkTelemetryStream:
    """Bronze files -> quality audit -> deduplicated Silver -> final time windows.

    Every boundary is a native Parquet file sink with its own checkpoint.
    Invalid and late inputs remain in the quality audit. Only valid rows enter
    Silver; deduplication is bounded by the event-time watermark.
    """

    STAGES = ("quality", "silver", "analytics")
    VERSION = 1

    def __init__(
        self,
        spark: SparkSession,
        input_directory: str | Path,
        schema: StructType,
        output_directory: str | Path = "data/streaming",
        *,
        watermark_seconds: int = 10,
        window_seconds: int = 10,
        max_files_per_trigger: int = 1,
    ):
        for name, value in (
            ("watermark_seconds", watermark_seconds),
            ("window_seconds", window_seconds),
            ("max_files_per_trigger", max_files_per_trigger),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.spark = spark
        self.input_directory = Path(input_directory).resolve()
        self.output_directory = Path(output_directory).resolve()
        if (
            self.input_directory == self.output_directory
            or self.input_directory in self.output_directory.parents
            or self.output_directory in self.input_directory.parents
        ):
            raise ValueError("Input and output directories must be separate, non-nested paths")
        if not self.input_directory.is_dir():
            raise FileNotFoundError(f"Streaming input directory not found: {self.input_directory}")
        self.schema = schema
        self.watermark = f"{watermark_seconds} seconds"
        self.window = f"{window_seconds} seconds"
        self.max_files_per_trigger = max_files_per_trigger
        # Analyze the same stateless transform used by batch Silver, before starting queries.
        self.quality_schema = SparkSilverTelemetryProcessor.transform(
            spark.createDataFrame([], schema)
        ).schema
        self.paths = {stage: self.output_directory / stage for stage in self.STAGES}
        self.checkpoints = self.output_directory / "checkpoints"
        self.query_prefix = (
            "telemetry_" + hashlib.sha256(str(self.output_directory).encode()).hexdigest()[:12]
        )
        self.configuration = {
            "version": self.VERSION,
            "input_directory": str(self.input_directory),
            "output_directory": str(self.output_directory),
            "schema": schema.jsonValue(),
            "watermark": self.watermark,
            "window": self.window,
            "silver_schema_version": SparkSilverTelemetryProcessor.SCHEMA_VERSION,
            "shuffle_partitions": spark.conf.get("spark.sql.shuffle.partitions"),
            "time_zone": spark.conf.get("spark.sql.session.timeZone"),
        }

    def _prepare(self) -> None:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        config_path = self.output_directory / "_stream_config.json"
        try:
            with config_path.open("x", encoding="utf-8") as file:
                json.dump(self.configuration, file, indent=2)
        except FileExistsError:
            if json.loads(config_path.read_text(encoding="utf-8")) != self.configuration:
                raise ValueError(
                    "Streaming configuration changed; use a new output directory and checkpoints"
                ) from None
        for path in self.paths.values():
            path.mkdir(parents=True, exist_ok=True)

    def _read(self, path: Path, schema: StructType) -> DataFrame:
        return (
            self.spark.readStream.schema(schema)
            .option("maxFilesPerTrigger", self.max_files_per_trigger)
            .parquet(str(path))
        )

    def dataframe(self, stage: str) -> DataFrame:
        if stage == "quality":
            return SparkSilverTelemetryProcessor.transform(
                self._read(self.input_directory, self.schema)
            )
        if stage == "silver":
            return (
                self._read(self.paths["quality"], self.quality_schema)
                .filter(F.col("is_valid"))
                .withWatermark("timestamp", self.watermark)
                .dropDuplicatesWithinWatermark(["session_id", "sample_index"])
            )
        if stage == "analytics":
            return (
                self._read(self.paths["silver"], self.quality_schema)
                .withWatermark("timestamp", self.watermark)
                .groupBy(F.window("timestamp", self.window), "session_id", "car_id", "track_id")
                .agg(
                    F.count("*").alias("sample_count"),
                    F.avg("vehicle_speed_kmh").alias("average_speed_kmh"),
                    F.max("vehicle_speed_kmh").alias("maximum_speed_kmh"),
                    F.avg("front_pressure_psi").alias("average_front_pressure_psi"),
                    F.avg("rear_pressure_psi").alias("average_rear_pressure_psi"),
                    F.avg("front_core_temp_c").alias("average_front_core_temp_c"),
                    F.avg("rear_core_temp_c").alias("average_rear_core_temp_c"),
                )
                .select(
                    "window.start",
                    "window.end",
                    "session_id",
                    "car_id",
                    "track_id",
                    "sample_count",
                    "average_speed_kmh",
                    "maximum_speed_kmh",
                    "average_front_pressure_psi",
                    "average_rear_pressure_psi",
                    "average_front_core_temp_c",
                    "average_rear_core_temp_c",
                )
            )
        raise ValueError(f"Unknown streaming stage: {stage}")

    def start_stage(
        self, stage: str, *, available_now: bool = False, trigger_seconds: int = 2
    ) -> StreamingQuery:
        if stage not in self.STAGES:
            raise ValueError(f"Unknown streaming stage: {stage}")
        if trigger_seconds <= 0:
            raise ValueError("trigger_seconds must be positive")
        self._prepare()
        writer = (
            self.dataframe(stage)
            .writeStream.format("parquet")
            .outputMode("append")
            .queryName(f"{self.query_prefix}_{stage}")
            .option("path", str(self.paths[stage]))
            .option("checkpointLocation", str(self.checkpoints / stage))
        )
        if available_now:
            return writer.trigger(availableNow=True).start()
        return writer.trigger(processingTime=f"{trigger_seconds} seconds").start()

    def start(self, *, trigger_seconds: int = 2) -> TelemetryStreamingQueries:
        result = TelemetryStreamingQueries({})
        try:
            for stage in self.STAGES:
                result.queries[stage] = self.start_stage(stage, trigger_seconds=trigger_seconds)
        except Exception:
            result.stop()
            raise
        return result

    def run_available(self, *, timeout_seconds: int = 180) -> dict[str, dict | None]:
        """Drain each boundary in order and stop; preserve state for the next run."""
        progress = {}
        for stage in self.STAGES:
            query = self.start_stage(stage, available_now=True)
            try:
                if not query.awaitTermination(timeout_seconds):
                    raise TimeoutError(f"Streaming stage {stage} did not finish in time")
                progress[stage] = query.lastProgress
            finally:
                if query.isActive:
                    query.stop()
        return progress

    def read_quarantine(self) -> DataFrame:
        """Read the committed audit sink, including rows with missing event time."""
        return (
            self.spark.read.schema(self.quality_schema)
            .parquet(str(self.paths["quality"]))
            .filter(~F.col("is_valid"))
        )
