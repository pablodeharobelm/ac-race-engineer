from pathlib import Path

from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)


def main():

    bronze_directory = Path(
        "data/bronze/telemetry"
    )

    bronze_files = list(
        bronze_directory.rglob(
            "telemetry.parquet"
        )
    )

    if not bronze_files:
        raise FileNotFoundError(
            "No Bronze telemetry found. "
            "Run bronze_demo first."
        )

    latest_bronze = max(
        bronze_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    processor = (
        SilverTelemetryProcessor()
    )

    result = processor.process(
        latest_bronze
    )

    print()
    print("SILVER PROCESSING")
    print("=================")
    print()

    print(
        f"Session: "
        f"{result.session_id}"
    )

    print(
        f"Status: "
        f"{result.status}"
    )

    print()

    print(
        f"Input rows: "
        f"{result.input_rows}"
    )

    print(
        f"Output rows: "
        f"{result.output_rows}"
    )

    print(
        "Duplicates removed: "
        f"{result.duplicate_rows_removed}"
    )

    print(
        "Quarantined rows: "
        f"{result.quarantined_rows}"
    )

    print()

    print(
        f"Silver: "
        f"{result.output_file}"
    )

    if (
        result.quarantine_file
        is not None
    ):
        print(
            f"Quarantine: "
            f"{result.quarantine_file}"
        )

    print()

    print(
        f"Manifest: "
        f"{result.manifest_file}"
    )


if __name__ == "__main__":
    main()

