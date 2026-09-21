from pathlib import Path

from ac_race_engineer.analysis.brake_analyzer import (
    BrakeAnalyzer,
)
from ac_race_engineer.analysis.dynamics_analyzer import (
    VehicleDynamicsAnalyzer,
)
from ac_race_engineer.analysis.suspension_analyzer import (
    SuspensionAnalyzer,
)
from ac_race_engineer.analysis.tyre_analyzer import (
    TyreAnalyzer,
)
from ac_race_engineer.domain.experiment import (
    BrakeExperimentDelta,
    DynamicsExperimentDelta,
    ExperimentComparison,
    MetricDelta,
    SuspensionExperimentDelta,
    TyreExperimentDelta,
)
from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.services.setup_service import (
    SetupService,
)


class ExperimentService:

    def __init__(self):
        self.tyre_analyzer = TyreAnalyzer()
        self.brake_analyzer = BrakeAnalyzer()
        self.suspension_analyzer = SuspensionAnalyzer()
        self.dynamics_analyzer = VehicleDynamicsAnalyzer()

    @staticmethod
    def _delta(
        baseline: float,
        candidate: float,
    ) -> MetricDelta:

        return MetricDelta(
            baseline=baseline,
            candidate=candidate,
            delta=candidate - baseline,
        )

    def compare(
        self,
        baseline_setup: CarSetup,
        candidate_setup: CarSetup,
        baseline_session: str | Path,
        candidate_session: str | Path,
    ) -> ExperimentComparison:

        if baseline_setup.car_id != candidate_setup.car_id:
            raise ValueError(
                "Cannot compare experiments from different cars"
            )

        setup_comparison = SetupService.compare(
            setup_a=baseline_setup,
            setup_b=candidate_setup,
        )

        baseline_tyres = self.tyre_analyzer.analyze(
            baseline_session
        )

        candidate_tyres = self.tyre_analyzer.analyze(
            candidate_session
        )

        baseline_brakes = self.brake_analyzer.analyze(
            baseline_session
        )

        candidate_brakes = self.brake_analyzer.analyze(
            candidate_session
        )

        baseline_suspension = (
            self.suspension_analyzer.analyze(
                baseline_session
            )
        )

        candidate_suspension = (
            self.suspension_analyzer.analyze(
                candidate_session
            )
        )

        baseline_dynamics = (
            self.dynamics_analyzer.analyze(
                baseline_session
            )
        )

        candidate_dynamics = (
            self.dynamics_analyzer.analyze(
                candidate_session
            )
        )

        self._validate_sessions(
            baseline_setup=baseline_setup,
            candidate_setup=candidate_setup,
            baseline_car_id=baseline_tyres.car_id,
            candidate_car_id=candidate_tyres.car_id,
            baseline_track_id=baseline_tyres.track_id,
            candidate_track_id=candidate_tyres.track_id,
        )

        tyre_deltas = {}

        for position in baseline_tyres.wheels:

            baseline = baseline_tyres.wheels[position]
            candidate = candidate_tyres.wheels[position]

            tyre_deltas[position] = (
                TyreExperimentDelta(
                    pressure_psi=self._delta(
                        baseline.average_pressure_psi,
                        candidate.average_pressure_psi,
                    ),
                    core_temperature_c=self._delta(
                        baseline.average_core_temp_c,
                        candidate.average_core_temp_c,
                    ),
                )
            )

        brake_deltas = {}

        for position in baseline_brakes.wheels:

            baseline = baseline_brakes.wheels[position]
            candidate = candidate_brakes.wheels[position]

            brake_deltas[position] = (
                BrakeExperimentDelta(
                    average_temperature_c=self._delta(
                        baseline.average_temperature_c,
                        candidate.average_temperature_c,
                    ),
                    peak_temperature_c=self._delta(
                        baseline.peak_temperature_c,
                        candidate.peak_temperature_c,
                    ),
                )
            )

        suspension_deltas = {}

        for position in baseline_suspension.wheels:

            baseline = baseline_suspension.wheels[position]
            candidate = candidate_suspension.wheels[position]

            suspension_deltas[position] = (
                SuspensionExperimentDelta(
                    average_travel_mm=self._delta(
                        baseline.average_travel_mm,
                        candidate.average_travel_mm,
                    ),
                    average_load_n=self._delta(
                        baseline.average_load_n,
                        candidate.average_load_n,
                    ),
                )
            )

        dynamics_delta = DynamicsExperimentDelta(
            front_slip_angle_deg=self._delta(
                baseline_dynamics.average_front_slip_angle_deg,
                candidate_dynamics.average_front_slip_angle_deg,
            ),
            rear_slip_angle_deg=self._delta(
                baseline_dynamics.average_rear_slip_angle_deg,
                candidate_dynamics.average_rear_slip_angle_deg,
            ),
            front_limited_percentage=self._delta(
                baseline_dynamics.front_limited_percentage,
                candidate_dynamics.front_limited_percentage,
            ),
            rear_limited_percentage=self._delta(
                baseline_dynamics.rear_limited_percentage,
                candidate_dynamics.rear_limited_percentage,
            ),
            maximum_lateral_g=self._delta(
                baseline_dynamics.maximum_lateral_g,
                candidate_dynamics.maximum_lateral_g,
            ),
        )

        return ExperimentComparison(
            car_id=baseline_tyres.car_id,
            track_id=baseline_tyres.track_id,
            setup_changes=setup_comparison,
            tyres=tyre_deltas,
            brakes=brake_deltas,
            suspension=suspension_deltas,
            dynamics=dynamics_delta,
        )

    @staticmethod
    def _validate_sessions(
        baseline_setup: CarSetup,
        candidate_setup: CarSetup,
        baseline_car_id: str,
        candidate_car_id: str,
        baseline_track_id: str,
        candidate_track_id: str,
    ) -> None:

        if baseline_car_id != candidate_car_id:
            raise ValueError(
                "Sessions belong to different cars"
            )

        if baseline_track_id != candidate_track_id:
            raise ValueError(
                "Sessions belong to different tracks"
            )

        if baseline_setup.car_id != baseline_car_id:
            raise ValueError(
                "Baseline setup does not match session car"
            )

        if candidate_setup.car_id != candidate_car_id:
            raise ValueError(
                "Candidate setup does not match session car"
            )