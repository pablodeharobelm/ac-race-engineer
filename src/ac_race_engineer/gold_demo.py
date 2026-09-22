from pathlib import Path

import pandas as pd

from ac_race_engineer.lakehouse.gold import (
    GoldSessionAggregator,
)


def main():

    silver_directory = Path(
        "data/silver/telemetry"
    )

    silver_files = list(
        silver_directory.rglob(
            "telemetry.parquet"
        )
    )

    if not silver_files:
        raise FileNotFoundError(
            "No Silver telemetry found. "
            "Run silver_demo first."
        )

    latest_silver = max(
        silver_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    aggregator = (
        GoldSessionAggregator()
    )

    result = aggregator.aggregate(
        latest_silver
    )

    dataframe = pd.read_parquet(
        result.output_file
    )

    row = dataframe.iloc[0]

    print()
    print("GOLD SESSION SUMMARY")
    print("====================")
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
        f"Source rows: "
        f"{result.source_rows}"
    )

    print()

    print(
        f"Max speed: "
        f"{row['maximum_speed_kmh']:.2f} km/h"
    )

    print(
        f"Average speed: "
        f"{row['average_speed_kmh']:.2f} km/h"
    )

    print(
        f"Max lateral G: "
        f"{row['maximum_lateral_g']:.3f}"
    )

    print(
        f"Max braking G: "
        f"{row['maximum_braking_g']:.3f}"
    )

    print(
        f"Fuel used: "
        f"{row['fuel_used_l']:.4f} L"
    )

    print()

    print(
        "Front pressure: "
        f"{row['average_front_pressure_psi']:.2f} PSI"
    )

    print(
        "Rear pressure: "
        f"{row['average_rear_pressure_psi']:.2f} PSI"
    )

    print(
        "Front tyre temp: "
        f"{row['average_front_core_temp_c']:.2f} C"
    )

    print(
        "Rear tyre temp: "
        f"{row['average_rear_core_temp_c']:.2f} C"
    )

    print()

    print(
        "Front slip: "
        f"{row['average_front_slip_angle_deg']:.3f} deg"
    )

    print(
        "Rear slip: "
        f"{row['average_rear_slip_angle_deg']:.3f} deg"
    )

    print()

    print(
        f"Gold file: "
        f"{result.output_file}"
    )


if __name__ == "__main__":
    main()