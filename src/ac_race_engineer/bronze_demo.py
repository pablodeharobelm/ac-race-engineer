from pathlib import Path

from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)


def main():

    raw_directory = Path(
        "data/raw"
    )

    raw_sessions = list(
        raw_directory.glob(
            "session_*.jsonl"
        )
    )

    if not raw_sessions:
        raise FileNotFoundError(
            "No RAW sessions found. "
            "Run the simulator first."
        )

    latest_session = max(
        raw_sessions,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    ingestor = (
        BronzeTelemetryIngestor()
    )

    result = ingestor.ingest(
        latest_session
    )

    print()
    print("BRONZE INGESTION")
    print("================")
    print()

    print(
        f"Session: "
        f"{result.session_id}"
    )

    print(
        f"Status: "
        f"{result.status}"
    )

    print(
        f"Rows: "
        f"{result.row_count}"
    )

    print(
        f"Date: "
        f"{result.partition_date}"
    )

    print(
        f"Car: "
        f"{result.car_id}"
    )

    print(
        f"Track: "
        f"{result.track_id}"
    )

    print()

    print(
        f"Bronze file: "
        f"{result.output_file}"
    )


if __name__ == "__main__":
    main()