from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ac_race_engineer.domain.lakehouse import (
    BronzeIngestionResult,
)
from ac_race_engineer.domain.session import (
    SessionMetadata,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)


class BronzeTelemetryIngestor:

    SCHEMA_VERSION = 1

    def __init__(
        self,
        output_directory: str | Path = (
            "data/bronze/telemetry"
        ),
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def ingest(
        self,
        source_file: str | Path,
    ) -> BronzeIngestionResult:

        source_file = Path(
            source_file
        )

        if not source_file.exists():
            raise FileNotFoundError(
                f"RAW telemetry file not found: "
                f"{source_file}"
            )

        metadata_file = (
            source_file.with_suffix(
                ".metadata.json"
            )
        )

        if not metadata_file.exists():
            raise FileNotFoundError(
                f"Session metadata not found: "
                f"{metadata_file}"
            )

        metadata = (
            SessionMetadata
            .model_validate_json(
                metadata_file.read_text(
                    encoding="utf-8"
                )
            )
        )

        partition_date = (
            metadata.started_at
            .date()
            .isoformat()
        )

        output_file = (
            self.output_directory
            / f"date={partition_date}"
            / f"car_id={metadata.car_id}"
            / f"track_id={metadata.track_id}"
            / f"session_id={metadata.session_id}"
            / "telemetry.parquet"
        )

        if output_file.exists():

            parquet_metadata = (
                pq.ParquetFile(
                    output_file
                ).metadata
            )

            return BronzeIngestionResult(
                session_id=(
                    metadata.session_id
                ),
                row_count=(
                    parquet_metadata.num_rows
                ),
                output_file=str(
                    output_file
                ),
                status="skipped",
                partition_date=(
                    partition_date
                ),
                car_id=metadata.car_id,
                track_id=(
                    metadata.track_id
                ),
            )

        rows = self._read_raw_session(
            source_file=source_file,
            metadata=metadata,
        )

        if len(rows) != metadata.sample_count:
            raise ValueError(
                "RAW row count does not match "
                "session metadata sample_count"
            )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        table = pa.Table.from_pylist(
            rows
        )

        pq.write_table(
            table,
            output_file,
            compression="snappy",
        )

        return BronzeIngestionResult(
            session_id=metadata.session_id,
            row_count=len(rows),
            output_file=str(
                output_file
            ),
            status="written",
            partition_date=partition_date,
            car_id=metadata.car_id,
            track_id=metadata.track_id,
        )

    def _read_raw_session(
        self,
        source_file: Path,
        metadata: SessionMetadata,
    ) -> list[dict]:

        rows = []

        ingested_at = datetime.now(timezone.utc)

        with source_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                frame = (
                    TelemetryFrame
                    .model_validate_json(
                        line
                    )
                )

                self._validate_frame(
                    frame=frame,
                    metadata=metadata,
                )

                rows.append(
                    self._flatten_frame(
                        frame=frame,
                        metadata=metadata,
                        source_file=source_file,
                        ingested_at=(
                            ingested_at
                        ),
                    )
                )

        if not rows:
            raise ValueError(
                "RAW telemetry session is empty"
            )

        return rows

    @staticmethod
    def _validate_frame(
        frame: TelemetryFrame,
        metadata: SessionMetadata,
    ) -> None:

        if (
            frame.session_id
            != metadata.session_id
        ):
            raise ValueError(
                "Telemetry session_id does not "
                "match session metadata"
            )

        if (
            frame.car_id
            != metadata.car_id
        ):
            raise ValueError(
                "Telemetry car_id does not "
                "match session metadata"
            )

        if (
            frame.track_id
            != metadata.track_id
        ):
            raise ValueError(
                "Telemetry track_id does not "
                "match session metadata"
            )

    def _flatten_frame(
        self,
        frame: TelemetryFrame,
        metadata: SessionMetadata,
        source_file: Path,
        ingested_at: datetime,
    ) -> dict:

        row = {
            "timestamp": frame.timestamp,
            "session_id": (
                frame.session_id
            ),
            "sample_index": (
                frame.sample_index
            ),
            "elapsed_seconds": (
                frame.elapsed_seconds
            ),
            "car_id": frame.car_id,
            "track_id": frame.track_id,
            "setup_id": metadata.setup_id,
            "session_type": (
                metadata.session_type.value
            ),
            "telemetry_source": (
                metadata.source
            ),
            "source_file": (
                source_file.name
            ),
            "ingested_at": ingested_at,
            "schema_version": (
                self.SCHEMA_VERSION
            ),
        }

        for (
            key,
            value,
        ) in frame.vehicle.model_dump().items():

            row[
                f"vehicle_{key}"
            ] = value

        for (
            key,
            value,
        ) in (
            frame.environment
            .model_dump()
            .items()
        ):

            row[
                f"environment_{key}"
            ] = value

        for (
            position,
            wheel,
        ) in frame.wheels.items():

            prefix = (
                position.lower()
            )

            for (
                key,
                value,
            ) in wheel.model_dump().items():

                row[
                    f"{prefix}_{key}"
                ] = value

        return row


