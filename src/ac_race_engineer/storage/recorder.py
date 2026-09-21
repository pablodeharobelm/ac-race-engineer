from pathlib import Path

from ac_race_engineer.telemetry.source import TelemetrySource


class SessionRecorder:
    def __init__(
        self,
        source: TelemetrySource,
        output_directory: str = "data/raw",
    ):
        self.source = source
        self.output_directory = Path(output_directory)

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record_samples(
        self,
        sample_count: int,
    ) -> Path:
        if sample_count <= 0:
            raise ValueError("sample_count must be greater than 0")

        first_frame = self.source.read_frame()

        output_file = (
            self.output_directory
            / f"session_{first_frame.session_id}.jsonl"
        )

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            file.write(
                first_frame.model_dump_json()
                + "\n"
            )

            for _ in range(sample_count - 1):
                frame = self.source.read_frame()

                file.write(
                    frame.model_dump_json()
                    + "\n"
                )

        return output_file