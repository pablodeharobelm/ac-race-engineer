import argparse
import json
import time
from pathlib import Path

from ac_race_engineer.kafka.client import (
    KafkaTelemetryProducer,
    consume_telemetry,
    create_telemetry_topic,
)
from ac_race_engineer.spark.kafka import KafkaTelemetryStream
from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.telemetry.simulator import SimulatorSource


def main():
    parser = argparse.ArgumentParser(
        description="Kafka telemetry producer, inspector and Spark consumer"
    )
    parser.add_argument("command", choices=["topic", "produce", "consume", "stream"])
    parser.add_argument("--bootstrap", default="127.0.0.1:9092")
    parser.add_argument("--topic", default="telemetry.raw")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--hz", type=int, default=20)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--available-now", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/kafka_stream"))
    args = parser.parse_args()
    if args.samples <= 0 or args.hz <= 0:
        parser.error("samples and hz must be positive")
    if args.command == "topic":
        create_telemetry_topic(args.bootstrap, args.topic)
        print(f"Topic ready: {args.topic}")
    elif args.command == "produce":
        source = SimulatorSource(hz=args.hz, seed=42)
        producer = KafkaTelemetryProducer(args.bootstrap, args.topic, setup_id="kafka-demo")
        try:
            count = 0
            while args.continuous or count < args.samples:
                producer.send(source.read_frame())
                count += 1
                if count % args.samples == 0:
                    print(f"Acknowledged: {producer.flush()}", flush=True)
                if args.continuous:
                    time.sleep(1 / args.hz)
        except KeyboardInterrupt:
            pass
        finally:
            print(f"Acknowledged total: {producer.flush()}")
    elif args.command == "consume":
        for message in consume_telemetry(args.bootstrap, args.topic, limit=args.samples):
            print(message.model_dump_json())
    else:
        spark = create_spark_session(
            app_name="AC Race Engineer Kafka", master="local[2]", enable_kafka=True
        )
        running = None
        try:
            stream = KafkaTelemetryStream(spark, args.bootstrap, args.topic, args.output)
            if args.available_now:
                print(json.dumps(stream.run_available(), indent=2, default=str))
            else:
                running = stream.start()
                print("Kafka streaming active; Ctrl+C stops and preserves checkpoints.", flush=True)
                while True:
                    running.check()
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if running is not None:
                running.stop()
            spark.stop()


if __name__ == "__main__":
    main()
