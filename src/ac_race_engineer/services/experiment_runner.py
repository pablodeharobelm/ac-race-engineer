import uuid
from datetime import UTC, datetime
from pathlib import Path

from ac_race_engineer.domain.experiment import (
    ExperimentRunResult,
)
from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.experiment_service import (
    ExperimentService,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


class ExperimentRunner:

    def __init__(
        self,
        output_directory: str | Path = "data/experiments",
        session_directory: str | Path = "data/raw/experiments",
    ):
        self.output_directory = Path(
            output_directory
        )

        self.session_directory = Path(
            session_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.session_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.experiment_service = (
            ExperimentService()
        )

    def run(
        self,
        baseline_setup: CarSetup,
        candidate_setup: CarSetup,
        seed: int = 42,
        hz: int = 20,
        sample_count: int = 1200,
    ) -> ExperimentRunResult:

        if (
            baseline_setup.car_id
            != candidate_setup.car_id
        ):
            raise ValueError(
                "Experiment setups must belong "
                "to the same car"
            )

        if hz <= 0:
            raise ValueError(
                "hz must be greater than 0"
            )

        if sample_count <= 0:
            raise ValueError(
                "sample_count must be greater than 0"
            )

        experiment_id = str(
            uuid.uuid4()
        )

        experiment_sessions = (
            self.session_directory
            / experiment_id
        )

        baseline_session = (
            self._record_session(
                setup=baseline_setup,
                seed=seed,
                hz=hz,
                sample_count=sample_count,
                directory=(
                    experiment_sessions
                    / "baseline"
                ),
            )
        )

        candidate_session = (
            self._record_session(
                setup=candidate_setup,
                seed=seed,
                hz=hz,
                sample_count=sample_count,
                directory=(
                    experiment_sessions
                    / "candidate"
                ),
            )
        )

        comparison = (
            self.experiment_service.compare(
                baseline_setup=baseline_setup,
                candidate_setup=candidate_setup,
                baseline_session=baseline_session,
                candidate_session=candidate_session,
            )
        )

        result = ExperimentRunResult(
            experiment_id=experiment_id,
            created_at=datetime.now(UTC),
            seed=seed,
            hz=hz,
            sample_count=sample_count,
            baseline_setup_id=(
                baseline_setup.setup_id
            ),
            candidate_setup_id=(
                candidate_setup.setup_id
            ),
            comparison=comparison,
        )

        self._save_result(
            result
        )

        return result

    @staticmethod
    def _record_session(
        setup: CarSetup,
        seed: int,
        hz: int,
        sample_count: int,
        directory: Path,
    ) -> Path:

        simulator = SimulatorSource(
            hz=hz,
            seed=seed,
            setup=setup,
        )

        recorder = SessionRecorder(
            source=simulator,
            output_directory=str(
                directory
            ),
        )

        return recorder.record_samples(
            sample_count=sample_count,
            session_type=SessionType.TEST,
            setup_id=setup.setup_id,
        )

    def _save_result(
        self,
        result: ExperimentRunResult,
    ) -> Path:

        file_path = (
            self.output_directory
            / f"{result.experiment_id}.json"
        )

        file_path.write_text(
            result.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return file_path

