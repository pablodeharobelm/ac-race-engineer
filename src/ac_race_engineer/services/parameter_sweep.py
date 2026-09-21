import csv
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.domain.sweep import (
    ParameterSweepResult,
    SweepPoint,
)
from ac_race_engineer.services.experiment_runner import (
    ExperimentRunner,
)


class ParameterSweepRunner:

    def __init__(
        self,
        output_directory: str | Path = "data/sweeps",
        experiment_directory: str | Path = "data/experiments",
        session_directory: str | Path = "data/raw/experiments",
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.experiment_runner = ExperimentRunner(
            output_directory=experiment_directory,
            session_directory=session_directory,
        )

    def run(
        self,
        baseline_setup: CarSetup,
        parameter: str,
        values: list[float],
        seed: int = 42,
        hz: int = 20,
        sample_count: int = 1200,
    ) -> ParameterSweepResult:

        if parameter not in baseline_setup.values:
            raise ValueError(
                f"Baseline setup does not contain parameter: {parameter}"
            )

        if not values:
            raise ValueError(
                "Sweep requires at least one value"
            )

        sweep_id = str(
            uuid.uuid4()
        )

        points = []

        for value in values:

            candidate_values = dict(
                baseline_setup.values
            )

            candidate_values[
                parameter
            ] = value

            candidate_setup = CarSetup(
                car_id=baseline_setup.car_id,
                name=(
                    f"{baseline_setup.name} | "
                    f"{parameter}={value}"
                ),
                values=candidate_values,
            )

            experiment = (
                self.experiment_runner.run(
                    baseline_setup=baseline_setup,
                    candidate_setup=candidate_setup,
                    seed=seed,
                    hz=hz,
                    sample_count=sample_count,
                )
            )

            comparison = (
                experiment.comparison
            )

            front_pressure = (
                comparison.tyres["FL"]
                .pressure_psi.candidate
                + comparison.tyres["FR"]
                .pressure_psi.candidate
            ) / 2

            rear_pressure = (
                comparison.tyres["RL"]
                .pressure_psi.candidate
                + comparison.tyres["RR"]
                .pressure_psi.candidate
            ) / 2

            front_temperature = (
                comparison.tyres["FL"]
                .core_temperature_c.candidate
                + comparison.tyres["FR"]
                .core_temperature_c.candidate
            ) / 2

            rear_temperature = (
                comparison.tyres["RL"]
                .core_temperature_c.candidate
                + comparison.tyres["RR"]
                .core_temperature_c.candidate
            ) / 2

            front_brake_temperature = (
                comparison.brakes["FL"]
                .average_temperature_c.candidate
                + comparison.brakes["FR"]
                .average_temperature_c.candidate
            ) / 2

            rear_brake_temperature = (
                comparison.brakes["RL"]
                .average_temperature_c.candidate
                + comparison.brakes["RR"]
                .average_temperature_c.candidate
            ) / 2

            front_suspension = (
                comparison.suspension["FL"]
                .average_travel_mm.candidate
                + comparison.suspension["FR"]
                .average_travel_mm.candidate
            ) / 2

            rear_suspension = (
                comparison.suspension["RL"]
                .average_travel_mm.candidate
                + comparison.suspension["RR"]
                .average_travel_mm.candidate
            ) / 2

            points.append(
                SweepPoint(
                    parameter_value=value,
                    experiment_id=(
                        experiment.experiment_id
                    ),
                    front_pressure_psi=(
                        front_pressure
                    ),
                    rear_pressure_psi=(
                        rear_pressure
                    ),
                    front_core_temperature_c=(
                        front_temperature
                    ),
                    rear_core_temperature_c=(
                        rear_temperature
                    ),
                    front_brake_temperature_c=(
                        front_brake_temperature
                    ),
                    rear_brake_temperature_c=(
                        rear_brake_temperature
                    ),
                    front_suspension_travel_mm=(
                        front_suspension
                    ),
                    rear_suspension_travel_mm=(
                        rear_suspension
                    ),
                    front_slip_angle_deg=(
                        comparison
                        .dynamics
                        .front_slip_angle_deg
                        .candidate
                    ),
                    rear_slip_angle_deg=(
                        comparison
                        .dynamics
                        .rear_slip_angle_deg
                        .candidate
                    ),
                    front_limited_percentage=(
                        comparison
                        .dynamics
                        .front_limited_percentage
                        .candidate
                    ),
                    rear_limited_percentage=(
                        comparison
                        .dynamics
                        .rear_limited_percentage
                        .candidate
                    ),
                    maximum_lateral_g=(
                        comparison
                        .dynamics
                        .maximum_lateral_g
                        .candidate
                    ),
                )
            )

        result = ParameterSweepResult(
            sweep_id=sweep_id,
            created_at=datetime.now(UTC),
            car_id=baseline_setup.car_id,
            parameter=parameter,
            baseline_value=(
                baseline_setup.values[
                    parameter
                ]
            ),
            seed=seed,
            hz=hz,
            sample_count=sample_count,
            points=points,
        )

        self._save_json(
            result
        )

        self._save_csv(
            result
        )

        return result

    def _save_json(
        self,
        result: ParameterSweepResult,
    ) -> Path:

        file_path = (
            self.output_directory
            / f"{result.sweep_id}.json"
        )

        file_path.write_text(
            result.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return file_path

    def _save_csv(
        self,
        result: ParameterSweepResult,
    ) -> Path:

        file_path = (
            self.output_directory
            / f"{result.sweep_id}.csv"
        )

        with file_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(
                    SweepPoint.model_fields
                ),
            )

            writer.writeheader()

            for point in result.points:
                writer.writerow(
                    point.model_dump()
                )

        return file_path