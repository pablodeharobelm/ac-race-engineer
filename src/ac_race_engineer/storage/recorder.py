from pathlib import Path

from ac_race_engineer.domain.session import (
    SessionConditions,
    SessionMetadata,
    SessionType,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)
from ac_race_engineer.telemetry.source import (
    TelemetrySource,
)


class SessionRecorder:

    def __init__(
        self,
        source: TelemetrySource,
        output_directory: str = "data/raw",
    ):
        self.source = source

        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record_samples(
        self,
        sample_count: int,
        session_type: SessionType = SessionType.PRACTICE,
        setup_id: str | None = None,
    ) -> Path:

        if sample_count <= 0:
            raise ValueError(
                "sample_count must be greater than 0"
            )

        first_frame = self.source.read_frame()

        telemetry_file = (
            self.output_directory
            / f"session_{first_frame.session_id}.jsonl"
        )

        last_frame = first_frame

        with telemetry_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                first_frame.model_dump_json()
                + "\n"
            )

            for _ in range(
                sample_count - 1
            ):

                frame = self.source.read_frame()

                self._validate_frame(
                    first_frame=first_frame,
                    frame=frame,
                )

                file.write(
                    frame.model_dump_json()
                    + "\n"
                )

                last_frame = frame

        self._write_metadata(
            first_frame=first_frame,
            last_frame=last_frame,
            telemetry_file=telemetry_file,
            sample_count=sample_count,
            session_type=session_type,
            setup_id=setup_id,
        )

        return telemetry_file

    def _write_metadata(
        self,
        first_frame: TelemetryFrame,
        last_frame: TelemetryFrame,
        telemetry_file: Path,
        sample_count: int,
        session_type: SessionType,
        setup_id: str | None,
    ) -> None:

        initial_conditions = (
            SessionConditions(
                air_temperature_c=(
                    first_frame
                    .environment
                    .air_temperature_c
                ),
                track_temperature_c=(
                    first_frame
                    .environment
                    .track_temperature_c
                ),
                grip_level=(
                    first_frame
                    .environment
                    .grip_level
                ),
            )
        )

        final_conditions = (
            SessionConditions(
                air_temperature_c=(
                    last_frame
                    .environment
                    .air_temperature_c
                ),
                track_temperature_c=(
                    last_frame
                    .environment
                    .track_temperature_c
                ),
                grip_level=(
                    last_frame
                    .environment
                    .grip_level
                ),
            )
        )

        duration = max(
            0.0,
            (
                last_frame.elapsed_seconds
                - first_frame.elapsed_seconds
            ),
        )

        metadata = SessionMetadata(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            setup_id=setup_id,
            source=self.source.source_name,
            session_type=session_type,
            started_at=first_frame.timestamp,
            ended_at=last_frame.timestamp,
            sample_count=sample_count,
            duration_seconds=duration,
            initial_conditions=(
                initial_conditions
            ),
            final_conditions=(
                final_conditions
            ),
        )

        metadata_file = (
            telemetry_file.with_suffix(
                ".metadata.json"
            )
        )

        metadata_file.write_text(
            metadata.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _validate_frame(
        first_frame: TelemetryFrame,
        frame: TelemetryFrame,
    ) -> None:

        if (
            frame.session_id
            != first_frame.session_id
        ):
            raise ValueError(
                "Telemetry source changed session "
                "while recording"
            )

        if (
            frame.car_id
            != first_frame.car_id
        ):
            raise ValueError(
                "Telemetry source changed car "
                "while recording"
            )

        if (
            frame.track_id
            != first_frame.track_id
        ):
            raise ValueError(
                "Telemetry source changed track "
                "while recording"
            )

