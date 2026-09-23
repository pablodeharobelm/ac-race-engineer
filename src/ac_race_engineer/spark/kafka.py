"""Kafka -> durable Bronze audit -> the existing streaming Silver/analytics layers."""

import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    BinaryType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from ac_race_engineer.domain.session import SessionType
from ac_race_engineer.kafka.client import validate_topic
from ac_race_engineer.spark.streaming import SparkTelemetryStream, TelemetryStreamingQueries
from ac_race_engineer.telemetry.models import EnvironmentTelemetry, VehicleTelemetry, WheelTelemetry


def numeric_schema(model) -> StructType:
    fields = []
    for name, field in model.model_fields.items():
        if field.annotation not in (float, int):
            raise TypeError(f"Unsupported telemetry field type: {model.__name__}.{name}")
        fields.append(StructField(name, LongType() if field.annotation is int else DoubleType()))
    return StructType(fields)


def message_schema() -> StructType:
    frame = StructType(
        [
            StructField("timestamp", StringType()),
            StructField("session_id", StringType()),
            StructField("sample_index", LongType()),
            StructField("elapsed_seconds", DoubleType()),
            StructField("car_id", StringType()),
            StructField("track_id", StringType()),
            StructField("vehicle", numeric_schema(VehicleTelemetry)),
            StructField("environment", numeric_schema(EnvironmentTelemetry)),
            StructField(
                "wheels",
                StructType(
                    [
                        StructField(position, numeric_schema(WheelTelemetry))
                        for position in ("FL", "FR", "RL", "RR")
                    ]
                ),
            ),
        ]
    )
    return StructType(
        [
            StructField("schema_version", IntegerType()),
            StructField("source", StringType()),
            StructField("session_type", StringType()),
            StructField("setup_id", StringType()),
            StructField("frame", frame),
            StructField("_corrupt_record", StringType()),
        ]
    )


def kafka_record_schema() -> StructType:
    return StructType(
        [
            StructField("key", BinaryType()),
            StructField("value", BinaryType()),
            StructField("topic", StringType()),
            StructField("partition", IntegerType()),
            StructField("offset", LongType()),
            StructField("timestamp", TimestampType()),
        ]
    )


def decode_kafka_records(records: DataFrame) -> DataFrame:
    parsed = records.withColumn(
        "_message",
        F.from_json(
            F.col("value").cast("string"),
            message_schema(),
            {"mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_corrupt_record"},
        ),
    )
    invalid_metadata = ~F.coalesce(
        (F.length(F.col("_message.source")) > 0)
        & F.col("_message.session_type").isin([item.value for item in SessionType])
        & (F.col("key").cast("string") == F.col("_message.frame.session_id")),
        F.lit(False),
    )
    error = (
        F.when(
            F.col("_message").isNull() | F.col("_message._corrupt_record").isNotNull(),
            F.lit("invalid_json"),
        )
        .when(
            ~F.coalesce(F.col("_message.schema_version") == 1, F.lit(False)),
            F.lit("unsupported_schema"),
        )
        .when(invalid_metadata, F.lit("invalid_metadata"))
    )
    columns = [
        F.try_to_timestamp("_message.frame.timestamp").alias("timestamp"),
        *[
            F.col(f"_message.frame.{name}").alias(name)
            for name in ("session_id", "sample_index", "elapsed_seconds", "car_id", "track_id")
        ],
        F.col("_message.setup_id").alias("setup_id"),
        F.col("_message.session_type").alias("session_type"),
        F.col("_message.source").alias("telemetry_source"),
        F.concat(
            F.lit("kafka://"),
            F.col("topic"),
            F.lit("/"),
            F.col("partition"),
            F.lit("/"),
            F.col("offset"),
        ).alias("source_file"),
        F.current_timestamp().alias("ingested_at"),
        F.lit(1).alias("schema_version"),
        F.col("topic").alias("kafka_topic"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.col("key").alias("kafka_key"),
        F.col("value").alias("kafka_value"),
        error.alias("kafka_message_error"),
    ]
    for group, model in (("vehicle", VehicleTelemetry), ("environment", EnvironmentTelemetry)):
        columns.extend(
            F.col(f"_message.frame.{group}.{name}").alias(f"{group}_{name}")
            for name in model.model_fields
        )
    for position in ("FL", "FR", "RL", "RR"):
        columns.extend(
            F.col(f"_message.frame.wheels.{position}.{name}").alias(f"{position.lower()}_{name}")
            for name in WheelTelemetry.model_fields
        )
    return parsed.select(*columns)


class _KafkaSilverStream(SparkTelemetryStream):
    def transform(self, dataframe: DataFrame) -> DataFrame:
        return (
            super()
            .transform(dataframe)
            .withColumn("quality_invalid_message", F.col("kafka_message_error").isNotNull())
            .withColumn(
                "quality_issue_count",
                F.col("quality_issue_count") + F.col("quality_invalid_message").cast("int"),
            )
            .withColumn("is_valid", F.col("is_valid") & ~F.col("quality_invalid_message"))
        )


class KafkaTelemetryStream:
    def __init__(
        self,
        spark: SparkSession,
        bootstrap_servers: str = "127.0.0.1:9092",
        topic: str = "telemetry.raw",
        output_directory: str | Path = "data/kafka_stream",
        *,
        max_offsets_per_trigger: int = 1000,
        watermark_seconds: int = 10,
        window_seconds: int = 10,
    ):
        validate_topic(topic)
        if not bootstrap_servers.strip() or max_offsets_per_trigger <= 0:
            raise ValueError("A Kafka endpoint and positive max_offsets_per_trigger are required")
        self.spark = spark
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.output_directory = Path(output_directory).resolve()
        self.bronze_directory = self.output_directory / "bronze"
        self.bronze_directory.mkdir(parents=True, exist_ok=True)
        self.max_offsets_per_trigger = max_offsets_per_trigger
        schema = decode_kafka_records(spark.createDataFrame([], kafka_record_schema())).schema
        self.downstream = _KafkaSilverStream(
            spark,
            self.bronze_directory,
            schema,
            self.output_directory / "processed",
            watermark_seconds=watermark_seconds,
            window_seconds=window_seconds,
        )

    def start_bronze(self, *, available_now: bool = False) -> StreamingQuery:
        config = {
            "version": 1,
            "bootstrap_servers": self.bootstrap_servers,
            "topic": self.topic,
            "output_directory": str(self.output_directory),
            "starting_offsets": "earliest",
        }
        config_path = self.output_directory / "_kafka_config.json"
        try:
            with config_path.open("x", encoding="utf-8") as file:
                json.dump(config, file, indent=2)
        except FileExistsError:
            if json.loads(config_path.read_text(encoding="utf-8")) != config:
                raise ValueError(
                    "Kafka source changed; use a new output directory and checkpoints"
                ) from None
        # Check downstream configuration before consuming Kafka or advancing any offset.
        self.downstream._prepare()
        records = (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self.bootstrap_servers)
            .option("subscribe", self.topic)
            .option("startingOffsets", "earliest")
            .option("failOnDataLoss", "true")
            .option("kafka.allow.auto.create.topics", "false")
            .option("maxOffsetsPerTrigger", self.max_offsets_per_trigger)
            .load()
        )
        writer = (
            decode_kafka_records(records)
            .writeStream.format("parquet")
            .outputMode("append")
            .queryName(self.downstream.query_prefix + "_kafka_bronze")
            .option("path", str(self.bronze_directory))
            .option("checkpointLocation", str(self.output_directory / "kafka_checkpoint"))
        )
        return (
            writer.trigger(availableNow=True).start()
            if available_now
            else (writer.trigger(processingTime="2 seconds").start())
        )

    def run_available(self, *, timeout_seconds: int = 180) -> dict:
        query = self.start_bronze(available_now=True)
        try:
            if not query.awaitTermination(timeout_seconds):
                raise TimeoutError("Kafka Bronze did not finish in time")
            progress = {"bronze": query.lastProgress}
        finally:
            if query.isActive:
                query.stop()
        progress.update(self.downstream.run_available(timeout_seconds=timeout_seconds))
        return progress

    def start(self) -> TelemetryStreamingQueries:
        running = TelemetryStreamingQueries({})
        try:
            running.queries["bronze"] = self.start_bronze()
            running.queries.update(self.downstream.start().queries)
        except Exception:
            running.stop()
            raise
        return running
