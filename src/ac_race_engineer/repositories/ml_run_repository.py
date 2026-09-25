from pathlib import Path

from ac_race_engineer.domain.ml_tracking import (
    MLRunRecord,
)


class MLRunRepository:

    def __init__(
        self,
        file_path: str | Path = (
            "data/ml_tracking/runs.jsonl"
        ),
    ):
        self.file_path = Path(
            file_path
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        run: MLRunRecord,
    ) -> None:

        with self.file_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                run.model_dump_json()
                + "\n"
            )

    def list_all(
        self,
    ) -> list[MLRunRecord]:

        if not self.file_path.exists():
            return []

        runs = []

        with self.file_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                runs.append(
                    MLRunRecord
                    .model_validate_json(
                        line
                    )
                )

        return runs

    def get(
        self,
        run_id: str,
    ) -> MLRunRecord:

        for run in self.list_all():

            if run.run_id == run_id:
                return run

        raise FileNotFoundError(
            f"ML run not found: {run_id}"
        )

