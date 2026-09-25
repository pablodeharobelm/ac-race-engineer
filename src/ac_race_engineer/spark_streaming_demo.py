import argparse
import json
from pathlib import Path

from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.spark.streaming import SparkTelemetryStream
from ac_race_engineer.storage.stream_publisher import TelemetryStreamPublisher
from ac_race_engineer.telemetry.simulator import SimulatorSource


def main():
    parser = argparse.ArgumentParser(description="Simulate telemetry through Structured Streaming")
    parser.add_argument("--input", type=Path, default=Path("data/stream_input"))
    parser.add_argument("--output", type=Path, default=Path("data/streaming"))
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--samples-per-batch", type=int, default=20)
    parser.add_argument("--hz", type=int, default=20)
    parser.add_argument("--continuous", action="store_true", help="Publish at --hz until Ctrl+C")
    args = parser.parse_args()
    if args.batches <= 0 or args.samples_per_batch <= 0 or args.hz <= 0:
        parser.error("batches, samples-per-batch and hz must be positive")
    publisher = TelemetryStreamPublisher(
        SimulatorSource(hz=args.hz, seed=42), args.input, setup_id="stream-demo"
    )
    first = publisher.publish(args.samples_per_batch)
    spark = create_spark_session(
        app_name="AC Race Engineer Structured Streaming", master="local[2]"
    )
    running = None
    try:
        schema = spark.read.parquet(str(first)).schema
        stream = SparkTelemetryStream(spark, args.input, schema, args.output)
        if args.continuous:
            running = stream.start()
            print(
                "Streaming active; Ctrl+C stops the queries and preserves checkpoints.", flush=True
            )
            while True:
                running.check()
                publisher.publish(args.samples_per_batch, sample_interval_seconds=1 / args.hz)
        else:
            for _ in range(args.batches - 1):
                publisher.publish(args.samples_per_batch)
            progress = stream.run_available()
            print(json.dumps(progress, indent=2, default=str))
            print(f"Silver: {stream.paths['silver']}")
            print("Windows remain open until newer event timestamps advance the watermark.")
    except KeyboardInterrupt:
        print("Stopping streaming; restart with the same input and output to resume.")
    finally:
        if running is not None:
            running.stop()
        spark.stop()


if __name__ == "__main__":
    main()


