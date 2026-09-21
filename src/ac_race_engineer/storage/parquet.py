import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ac_race_engineer.telemetry.models import TelemetryFrame


class ParquetExporter:
    def convert_jsonl(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> Path:

        source_path = Path(source_file)

        if not source_path.exists():
            raise FileNotFoundError(source_path)

        if output_file is None:
            output_path = (
                source_path.parent
                / f"{source_path.stem}.parquet"
            )
        else:
            output_path = Path(output_file)

        rows = []

        with source_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1,
            ):
                line = line.strip()

                if not line:
                    continue

                raw_data = json.loads(line)

                frame = TelemetryFrame.model_validate(
                    raw_data
                )

                rows.append(
                    self._flatten_frame(frame)
                )

        if not rows:
            raise ValueError(
                "Cannot export empty telemetry session"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        table = pa.Table.from_pylist(rows)

        pq.write_table(
            table,
            output_path,
            compression="snappy",
        )

        return output_path

    @staticmethod
    def _flatten_frame(
        frame: TelemetryFrame,
    ) -> dict:

        row = {
            "timestamp": frame.timestamp,
            "session_id": frame.session_id,
            "sample_index": frame.sample_index,
            "elapsed_seconds": frame.elapsed_seconds,
            "car_id": frame.car_id,
            "track_id": frame.track_id,

            "speed_kmh": frame.vehicle.speed_kmh,
            "rpm": frame.vehicle.rpm,
            "gear": frame.vehicle.gear,

            "throttle": frame.vehicle.throttle,
            "brake": frame.vehicle.brake,
            "clutch": frame.vehicle.clutch,

            "steering_angle_deg":
                frame.vehicle.steering_angle_deg,

            "lateral_g":
                frame.vehicle.lateral_g,

            "longitudinal_g":
                frame.vehicle.longitudinal_g,

            "fuel_l":
                frame.vehicle.fuel_l,

            "brake_bias":
                frame.vehicle.brake_bias,

            "pitch_deg":
                frame.vehicle.pitch_deg,

            "roll_deg":
                frame.vehicle.roll_deg,

            "ride_height_front_mm":
                frame.vehicle.ride_height_front_mm,

            "ride_height_rear_mm":
                frame.vehicle.ride_height_rear_mm,

            "air_temperature_c":
                frame.environment.air_temperature_c,

            "track_temperature_c":
                frame.environment.track_temperature_c,

            "grip_level":
                frame.environment.grip_level,
        }

        for position, wheel in frame.wheels.items():

            prefix = position.lower()

            row[f"{prefix}_pressure_psi"] = (
                wheel.pressure_psi
            )

            row[f"{prefix}_tyre_temp_inner_c"] = (
                wheel.tyre_temp_inner_c
            )

            row[f"{prefix}_tyre_temp_middle_c"] = (
                wheel.tyre_temp_middle_c
            )

            row[f"{prefix}_tyre_temp_outer_c"] = (
                wheel.tyre_temp_outer_c
            )

            row[f"{prefix}_tyre_temp_core_c"] = (
                wheel.tyre_temp_core_c
            )

            row[f"{prefix}_brake_temp_c"] = (
                wheel.brake_temp_c
            )

            row[f"{prefix}_wheel_speed_kmh"] = (
                wheel.wheel_speed_kmh
            )

            row[f"{prefix}_load_n"] = (
                wheel.load_n
            )

            row[f"{prefix}_slip_ratio"] = (
                wheel.slip_ratio
            )

            row[f"{prefix}_slip_angle_deg"] = (
                wheel.slip_angle_deg
            )

            row[f"{prefix}_suspension_travel_mm"] = (
                wheel.suspension_travel_mm
            )

        return row