from pathlib import Path

from pyspark.sql import SparkSession

from ac_race_engineer.domain.lakehouse import (
    SparkSQLSessionSummary,
)


class SparkSQLSessionAnalyzer:

    VIEW_NAME = "silver_telemetry"

    def __init__(
        self,
        spark: SparkSession,
    ):
        self.spark = spark

    def analyze(
        self,
        silver_path: str | Path,
    ) -> SparkSQLSessionSummary:

        silver_path = Path(
            silver_path
        )

        if not silver_path.exists():
            raise FileNotFoundError(
                f"Silver dataset not found: "
                f"{silver_path}"
            )

        dataframe = (
            self.spark
            .read
            .parquet(
                str(
                    silver_path
                )
            )
        )

        if dataframe.limit(1).count() == 0:
            raise ValueError(
                "Silver dataset is empty"
            )

        dataframe.createOrReplaceTempView(
            self.VIEW_NAME
        )

        results = self.spark.sql(
            f"""
            SELECT
                session_id,
                car_id,
                track_id,

                COUNT(*) AS sample_count,

                MAX(elapsed_seconds)
                    - MIN(elapsed_seconds)
                    AS duration_seconds,

                MAX(vehicle_speed_kmh)
                    AS maximum_speed_kmh,

                AVG(vehicle_speed_kmh)
                    AS average_speed_kmh,

                AVG(front_pressure_psi)
                    AS average_front_pressure_psi,

                AVG(rear_pressure_psi)
                    AS average_rear_pressure_psi,

                AVG(front_core_temp_c)
                    AS average_front_core_temp_c,

                AVG(rear_core_temp_c)
                    AS average_rear_core_temp_c,

                AVG(front_brake_temp_c)
                    AS average_front_brake_temp_c,

                AVG(rear_brake_temp_c)
                    AS average_rear_brake_temp_c,

                AVG(front_slip_angle_deg)
                    AS average_front_slip_angle_deg,

                AVG(rear_slip_angle_deg)
                    AS average_rear_slip_angle_deg,

                AVG(
                    CASE
                        WHEN is_valid
                        THEN 1.0
                        ELSE 0.0
                    END
                ) * 100.0
                    AS valid_row_percentage

            FROM {self.VIEW_NAME}

            GROUP BY
                session_id,
                car_id,
                track_id
            """
        ).collect()

        if len(results) != 1:
            raise ValueError(
                "Expected exactly one session "
                "in Silver dataset"
            )

        row = results[0]

        return SparkSQLSessionSummary(
            session_id=str(
                row["session_id"]
            ),
            car_id=str(
                row["car_id"]
            ),
            track_id=str(
                row["track_id"]
            ),
            sample_count=int(
                row["sample_count"]
            ),
            duration_seconds=float(
                row["duration_seconds"]
            ),
            maximum_speed_kmh=float(
                row["maximum_speed_kmh"]
            ),
            average_speed_kmh=float(
                row["average_speed_kmh"]
            ),
            average_front_pressure_psi=float(
                row[
                    "average_front_pressure_psi"
                ]
            ),
            average_rear_pressure_psi=float(
                row[
                    "average_rear_pressure_psi"
                ]
            ),
            average_front_core_temp_c=float(
                row[
                    "average_front_core_temp_c"
                ]
            ),
            average_rear_core_temp_c=float(
                row[
                    "average_rear_core_temp_c"
                ]
            ),
            average_front_brake_temp_c=float(
                row[
                    "average_front_brake_temp_c"
                ]
            ),
            average_rear_brake_temp_c=float(
                row[
                    "average_rear_brake_temp_c"
                ]
            ),
            average_front_slip_angle_deg=float(
                row[
                    "average_front_slip_angle_deg"
                ]
            ),
            average_rear_slip_angle_deg=float(
                row[
                    "average_rear_slip_angle_deg"
                ]
            ),
            valid_row_percentage=float(
                row[
                    "valid_row_percentage"
                ]
            ),
        )

