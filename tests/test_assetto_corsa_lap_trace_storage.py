from pathlib import Path

import pyarrow.parquet as pq
import pytest

from ac_race_engineer.storage.lap_trace import (
    LapTraceParquetStore,
)
from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_tracker import (
    LapTrace,
)


def build_trace(
    *,
    lap_time_ms: int = 100000,
) -> LapTrace:
    return LapTrace(
        session_id="session-001",
        lap_number=1,
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        lap_time_ms=lap_time_ms,
        samples=(
            DrivingTraceSample(
                progress=0.01,
                elapsed_seconds=0.5,
                speed_kmh=120.0,
                throttle=1.0,
                brake=0.0,
                steering_angle_deg=0.0,
            ),
            DrivingTraceSample(
                progress=0.50,
                elapsed_seconds=50.0,
                speed_kmh=82.0,
                throttle=0.1,
                brake=0.8,
                steering_angle_deg=16.0,
            ),
            DrivingTraceSample(
                progress=0.98,
                elapsed_seconds=99.0,
                speed_kmh=145.0,
                throttle=1.0,
                brake=0.0,
                steering_angle_deg=1.0,
            ),
        ),
    )


def test_writes_lap_trace_to_expected_path(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    output_file = store.write(
        build_trace()
    )

    assert output_file == (
        tmp_path
        / "lap_traces"
        / "session_id=session-001"
        / "lap_number=0001"
        / "trace.parquet"
    )

    assert output_file.exists()


def test_parquet_contains_one_row_per_sample(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    output_file = store.write(
        build_trace()
    )

    parquet_file = pq.ParquetFile(
        output_file
    )

    assert (
        parquet_file.metadata.num_rows
        == 3
    )


def test_parquet_contains_required_columns(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    output_file = store.write(
        build_trace()
    )

    table = (
        pq.ParquetFile(
            output_file
        ).read()
    )

    assert (
        LapTraceParquetStore.REQUIRED_COLUMNS
        <= set(
            table.column_names
        )
    )


def test_parquet_contains_dataset_metadata(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    output_file = store.write(
        build_trace()
    )

    schema = (
        pq.ParquetFile(
            output_file
        ).schema_arrow
    )

    metadata = (
        schema.metadata
        or {}
    )

    assert (
        metadata[
            b"ac_race_engineer.dataset"
        ]
        == b"assetto_corsa_lap_trace"
    )

    assert (
        metadata[
            b"ac_race_engineer.schema_version"
        ]
        == b"1"
    )


def test_round_trip_preserves_trace(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    original = build_trace()

    store.write(
        original
    )

    restored = store.read(
        session_id="session-001",
        lap_number=1,
    )

    assert restored == original


def test_write_replaces_existing_trace(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
        / "lap_traces"
    )

    first = build_trace(
        lap_time_ms=100000
    )

    second = build_trace(
        lap_time_ms=99000
    )

    first_path = store.write(
        first
    )

    second_path = store.write(
        second
    )

    assert first_path == second_path

    restored = store.read(
        session_id="session-001",
        lap_number=1,
    )

    assert (
        restored.lap_time_ms
        == 99000
    )

    assert (
        len(
            list(
                second_path.parent.glob(
                    "*.parquet"
                )
            )
        )
        == 1
    )


def test_rejects_empty_trace(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
    )

    trace = LapTrace(
        session_id="session-001",
        lap_number=1,
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        lap_time_ms=100000,
        samples=(),
    )

    with pytest.raises(
        ValueError,
        match="empty LapTrace",
    ):
        store.write(
            trace
        )


def test_rejects_non_positive_lap_number(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
    )

    trace = LapTrace(
        session_id="session-001",
        lap_number=0,
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        lap_time_ms=100000,
        samples=(
            DrivingTraceSample(
                progress=0.0,
                elapsed_seconds=0.0,
                speed_kmh=100.0,
                throttle=1.0,
                brake=0.0,
                steering_angle_deg=0.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="lap_number",
    ):
        store.write(
            trace
        )


def test_rejects_non_positive_lap_time(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
    )

    trace = LapTrace(
        session_id="session-001",
        lap_number=1,
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        lap_time_ms=0,
        samples=(
            DrivingTraceSample(
                progress=0.0,
                elapsed_seconds=0.0,
                speed_kmh=100.0,
                throttle=1.0,
                brake=0.0,
                steering_angle_deg=0.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="lap_time_ms",
    ):
        store.write(
            trace
        )


def test_read_missing_trace_raises(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
    )

    with pytest.raises(
        FileNotFoundError
    ):
        store.read(
            session_id="missing-session",
            lap_number=1,
        )


def test_rejects_session_id_with_path_separator(
    tmp_path: Path,
) -> None:
    store = LapTraceParquetStore(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="path separators",
    ):
        store.path_for(
            session_id="invalid/session",
            lap_number=1,
        )

def test_optional_controls_roundtrip_and_legacy_columns(tmp_path):
    from dataclasses import replace
    store = LapTraceParquetStore(tmp_path)
    trace = build_trace()
    samples = tuple(replace(sample, gear=3, clutch=0.4) for sample in trace.samples)
    path = store.write(replace(trace, samples=samples))
    loaded = store.read_file(path)
    assert all(sample.gear == 3 and sample.clutch == 0.4 for sample in loaded.samples)
    table = pq.ParquetFile(path).read().drop(["gear", "clutch"])
    pq.write_table(table, path)
    legacy = store.read_file(path)
    assert all(sample.gear is None and sample.clutch is None for sample in legacy.samples)
