from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import (
    Base,
)
from ac_race_engineer.database.models import (
    LapTraceRecord,
    SessionRecord,
)
from ac_race_engineer.storage.lap_trace import (
    LapTraceParquetStore,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class TraceBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_index = 0

        self.graphics_values = (
            (
                0,
                0.01,
                500,
            ),
            (
                0,
                0.50,
                50000,
            ),
            (
                0,
                0.98,
                99000,
            ),
            (
                1,
                0.01,
                500,
            ),
        )

    def read_graphics(
        self,
    ):
        original = (
            super().read_graphics()
        )

        index = min(
            self.graphics_index,
            len(
                self.graphics_values
            )
            - 1,
        )

        (
            completed_laps,
            progress,
            current_time_ms,
        ) = self.graphics_values[
            index
        ]

        self.graphics_index += 1

        return replace(
            original,
            completed_laps=completed_laps,
            normalized_car_position=progress,
            current_time_ms=current_time_ms,
            last_time_ms=100000,
        )


def test_completed_trace_is_written_to_parquet_and_database(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    session = Session(
        engine
    )

    try:
        source = (
            AssettoCorsaSource(
                TraceBackend(),
                stale_timeout_seconds=None,
            )
        )

        trace_store = (
            LapTraceParquetStore(
                tmp_path
                / "lap_traces"
            )
        )

        persistence = (
            AssettoCorsaPersistenceService(
                session,
                trace_store=trace_store,
            )
        )

        for _ in range(
            4
        ):
            source.read_frame()

        result = (
            persistence.drain_source(
                source
            )
        )

        assert (
            result.laps_saved
            == 1
        )

        assert (
            result.traces_saved
            == 1
        )

        records = (
            persistence.lap_trace_repository.list_for_session(
                source.session_id
            )
        )

        assert len(
            records
        ) == 1

        record = records[0]

        assert (
            record.lap_number
            == 1
        )

        assert (
            record.lap_time_ms
            == 100000
        )

        assert (
            record.sample_count
            == 3
        )

        assert (
            record.progress_start
            == 0.01
        )

        assert (
            record.progress_end
            == 0.98
        )

        parquet_file = Path(
            record.parquet_path
        )

        assert (
            parquet_file.exists()
        )

        table = pq.read_table(
            parquet_file
        )

        assert (
            table.num_rows
            == 3
        )

    finally:
        session.close()
        engine.dispose()


def test_trace_parent_session_exists(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    session = Session(
        engine
    )

    try:
        source = (
            AssettoCorsaSource(
                TraceBackend(),
                stale_timeout_seconds=None,
            )
        )

        persistence = (
            AssettoCorsaPersistenceService(
                session,
                trace_directory=(
                    tmp_path
                    / "lap_traces"
                ),
            )
        )

        for _ in range(
            4
        ):
            source.read_frame()

        persistence.drain_source(
            source
        )

        parent = session.get(
            SessionRecord,
            source.session_id,
        )

        assert parent is not None

        assert (
            parent.source
            == "assetto_corsa"
        )

        assert (
            parent.session_type
            == "practice"
        )

    finally:
        session.close()
        engine.dispose()


def test_trace_metadata_matches_parquet(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    session = Session(
        engine
    )

    try:
        source = (
            AssettoCorsaSource(
                TraceBackend(),
                stale_timeout_seconds=None,
            )
        )

        trace_store = (
            LapTraceParquetStore(
                tmp_path
                / "lap_traces"
            )
        )

        persistence = (
            AssettoCorsaPersistenceService(
                session,
                trace_store=trace_store,
            )
        )

        for _ in range(
            4
        ):
            source.read_frame()

        persistence.drain_source(
            source
        )

        record = session.query(
            LapTraceRecord
        ).one()

        restored = (
            trace_store.read(
                session_id=record.session_id,
                lap_number=record.lap_number,
            )
        )

        assert (
            restored.lap_number
            == record.lap_number
        )

        assert (
            restored.lap_time_ms
            == record.lap_time_ms
        )

        assert (
            restored.sample_count
            == record.sample_count
        )

        assert (
            restored.samples[0].progress
            == record.progress_start
        )

        assert (
            restored.samples[-1].progress
            == record.progress_end
        )

    finally:
        session.close()
        engine.dispose()


def test_second_drain_does_not_duplicate_trace(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    session = Session(
        engine
    )

    try:
        source = (
            AssettoCorsaSource(
                TraceBackend(),
                stale_timeout_seconds=None,
            )
        )

        persistence = (
            AssettoCorsaPersistenceService(
                session,
                trace_directory=(
                    tmp_path
                    / "lap_traces"
                ),
            )
        )

        for _ in range(
            4
        ):
            source.read_frame()

        first = (
            persistence.drain_source(
                source
            )
        )

        second = (
            persistence.drain_source(
                source
            )
        )

        assert (
            first.traces_saved
            == 1
        )

        assert (
            second.traces_saved
            == 0
        )

        records = (
            persistence.lap_trace_repository.list_for_session(
                source.session_id
            )
        )

        assert len(
            records
        ) == 1

    finally:
        session.close()
        engine.dispose()