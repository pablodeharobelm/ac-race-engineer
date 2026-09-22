from pathlib import Path

from ac_race_engineer.lakehouse.pipeline import (
    LakehousePipeline,
)


def main():

    raw_directory = Path(
        "data/raw"
    )

    raw_files = list(
        raw_directory.glob(
            "session_*.jsonl"
        )
    )

    if not raw_files:
        raise FileNotFoundError(
            "No RAW sessions found."
        )

    latest_raw = max(
        raw_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    pipeline = (
        LakehousePipeline()
    )

    result = pipeline.run(
        latest_raw
    )

    print()
    print("LAKEHOUSE PIPELINE")
    print("==================")
    print()

    print(
        f"Session: "
        f"{result.session_id}"
    )

    print()

    print(
        "BRONZE"
    )

    print(
        f"  Status: "
        f"{result.bronze.status}"
    )

    print(
        f"  Rows: "
        f"{result.bronze.row_count}"
    )

    print()

    print(
        "SILVER"
    )

    print(
        f"  Status: "
        f"{result.silver.status}"
    )

    print(
        f"  Input: "
        f"{result.silver.input_rows}"
    )

    print(
        f"  Output: "
        f"{result.silver.output_rows}"
    )

    print(
        f"  Quarantine: "
        f"{result.silver.quarantined_rows}"
    )

    print()

    print(
        "GOLD"
    )

    print(
        f"  Status: "
        f"{result.gold.status}"
    )

    print(
        f"  Source rows: "
        f"{result.gold.source_rows}"
    )

    print(
        f"  Output rows: "
        f"{result.gold.output_rows}"
    )

    print()

    print(
        "Pipeline completed."
    )


if __name__ == "__main__":
    main()