from unittest.mock import Mock

import pyarrow.parquet as pq
import pytest

from ac_race_engineer.storage.stream_publisher import TelemetryStreamPublisher
from ac_race_engineer.telemetry.simulator import SimulatorSource


def test_publisher_preserves_session_and_publishes_complete_chunks(tmp_path):
    source = SimulatorSource(seed=42)
    publisher = TelemetryStreamPublisher(source, tmp_path, setup_id="stream")
    first = publisher.publish(3)
    second = publisher.publish(2)
    rows = pq.ParquetFile(first).read().to_pylist() + pq.ParquetFile(second).read().to_pylist()
    assert len(rows) == 5
    assert len({row["sample_index"] for row in rows}) == 5
    assert {row["session_id"] for row in rows} == {source.session_id}
    assert {row["setup_id"] for row in rows} == {"stream"}
    assert {row["telemetry_source"] for row in rows} == {"simulator"}
    assert "fl_pressure_psi" in rows[0]
    assert {path.name for path in tmp_path.iterdir()} == {first.name, second.name}


def test_publisher_does_not_expose_failed_write(tmp_path, monkeypatch):
    publisher = TelemetryStreamPublisher(SimulatorSource(seed=42), tmp_path)

    def fail_write(table, path, **kwargs):
        path.write_bytes(b"partial")
        raise OSError("disk failure")

    monkeypatch.setattr("ac_race_engineer.storage.stream_publisher.pq.write_table", fail_write)
    with pytest.raises(OSError, match="disk failure"):
        publisher.publish(2)
    assert list(tmp_path.iterdir()) == []


def test_publisher_rejects_session_change(tmp_path):
    source = Mock(source_name="simulator")
    source.read_frame.side_effect = [
        SimulatorSource(seed=1).read_frame(),
        SimulatorSource(seed=2).read_frame(),
    ]
    with pytest.raises(ValueError, match="changed session"):
        TelemetryStreamPublisher(source, tmp_path).publish(2)
    assert list(tmp_path.iterdir()) == []
