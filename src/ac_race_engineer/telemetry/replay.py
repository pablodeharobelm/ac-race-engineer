from pathlib import Path

import pyarrow.parquet as pq

from ac_race_engineer.telemetry.models import (
    EnvironmentTelemetry,
    TelemetryFrame,
    VehicleTelemetry,
    WheelTelemetry,
)
from ac_race_engineer.telemetry.source import (
    TelemetrySource,
)


class ReplaySource(TelemetrySource):

    def __init__(
        self,
        parquet_file: str | Path,
    ):
        self.parquet_file = Path(
            parquet_file
        )

        if not self.parquet_file.exists():
            raise FileNotFoundError(
                self.parquet_file
            )

        table = pq.read_table(
            self.parquet_file
        )

        self.rows = table.to_pylist()

        if not self.rows:
            raise ValueError(
                "Replay file contains no telemetry"
            )

        self.current_index = 0

    @property
    def source_name(self) -> str:
        return "replay"

    def read_frame(self) -> TelemetryFrame:

        if self.current_index >= len(self.rows):
            raise StopIteration(
                "Replay session finished"
            )

        row = self.rows[
            self.current_index
        ]

        self.current_index += 1

        wheels = {}

        for position in [
            "FL",
            "FR",
            "RL",
            "RR",
        ]:

            prefix = position.lower()

            wheels[position] = WheelTelemetry(
                pressure_psi=row[
                    f"{prefix}_pressure_psi"
                ],
                tyre_temp_inner_c=row[
                    f"{prefix}_tyre_temp_inner_c"
                ],
                tyre_temp_middle_c=row[
                    f"{prefix}_tyre_temp_middle_c"
                ],
                tyre_temp_outer_c=row[
                    f"{prefix}_tyre_temp_outer_c"
                ],
                tyre_temp_core_c=row[
                    f"{prefix}_tyre_temp_core_c"
                ],
                brake_temp_c=row[
                    f"{prefix}_brake_temp_c"
                ],
                wheel_speed_kmh=row[
                    f"{prefix}_wheel_speed_kmh"
                ],
                load_n=row[
                    f"{prefix}_load_n"
                ],
                slip_ratio=row[
                    f"{prefix}_slip_ratio"
                ],
                slip_angle_deg=row[
                    f"{prefix}_slip_angle_deg"
                ],
                suspension_travel_mm=row[
                    f"{prefix}_suspension_travel_mm"
                ],
            )

        vehicle = VehicleTelemetry(
            speed_kmh=row["speed_kmh"],
            rpm=row["rpm"],
            gear=row["gear"],
            throttle=row["throttle"],
            brake=row["brake"],
            clutch=row["clutch"],
            steering_angle_deg=row[
                "steering_angle_deg"
            ],
            lateral_g=row["lateral_g"],
            longitudinal_g=row[
                "longitudinal_g"
            ],
            fuel_l=row["fuel_l"],
            brake_bias=row["brake_bias"],
            pitch_deg=row["pitch_deg"],
            roll_deg=row["roll_deg"],
            ride_height_front_mm=row[
                "ride_height_front_mm"
            ],
            ride_height_rear_mm=row[
                "ride_height_rear_mm"
            ],
        )

        environment = EnvironmentTelemetry(
            air_temperature_c=row[
                "air_temperature_c"
            ],
            track_temperature_c=row[
                "track_temperature_c"
            ],
            grip_level=row[
                "grip_level"
            ],
        )

        return TelemetryFrame(
            timestamp=row["timestamp"],
            session_id=row["session_id"],
            sample_index=row["sample_index"],
            elapsed_seconds=row[
                "elapsed_seconds"
            ],
            car_id=row["car_id"],
            track_id=row["track_id"],
            vehicle=vehicle,
            environment=environment,
            wheels=wheels,
        )