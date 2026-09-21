import pyarrow.parquet as pq

from ac_race_engineer.storage.parquet import (
    ParquetExporter,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def test_export_session_to_parquet(tmp_path):

    simulator = SimulatorSource(
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    jsonl_file = recorder.record_samples(
        sample_count=100,
    )

    exporter = ParquetExporter()

    parquet_file = exporter.convert_jsonl(
        source_file=jsonl_file,
    )

    assert parquet_file.exists()

    table = pq.read_table(
        parquet_file
    )

    assert table.num_rows == 100

    assert "speed_kmh" in table.column_names
    assert "fl_pressure_psi" in table.column_names
    assert "rr_brake_temp_c" in table.column_names

from ac_race_engineer.telemetry.replay import (
    ReplaySource,
)


def test_replay_source_reads_parquet(tmp_path):

    simulator = SimulatorSource(
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=str(tmp_path),
    )

    jsonl_file = recorder.record_samples(
        sample_count=10,
    )

    exporter = ParquetExporter()

    parquet_file = exporter.convert_jsonl(
        source_file=jsonl_file,
    )

    replay = ReplaySource(
        parquet_file=parquet_file,
    )

    first_frame = replay.read_frame()

    assert first_frame.sample_index == 1
    assert first_frame.car_id == "mazda_mx5_cup"

    for _ in range(9):
        replay.read_frame()

    try:
        replay.read_frame()
    except StopIteration:
        pass
    else:
        raise AssertionError(
            "Expected replay to finish"
        )