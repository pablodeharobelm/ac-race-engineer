import pytest

from ac_race_engineer.dashboard.session_progress import summarize_pace


def test_pace_orders_laps_ignores_missing_times_and_keeps_laps_without_trace():
    result = summarize_pace([
        {"lap_number": 3, "lap_time_ms": 61000, "trace_available": False},
        {"lap_number": 1, "lap_time_ms": 62000},
        {"lap_number": 2, "lap_time_ms": 60000},
        {"lap_number": 4, "lap_time_ms": 0},
    ])
    assert result.best_number == 2
    assert result.best_ms == 60000
    assert result.average_ms == 61000
    assert result.change_ms == 1000
    assert result.spread_ms == pytest.approx(816.49658)
    assert result.laps[-1] == (3, 61000)


def test_sparse_sessions_do_not_claim_regularity():
    assert summarize_pace([]) is None
    single = summarize_pace([{"lap_number": 1, "lap_time_ms": 60000}])
    assert single.change_ms is None
    assert single.spread_ms is None
    pair = summarize_pace([{"lap_number": 1, "lap_time_ms": 61000}, {"lap_number": 2, "lap_time_ms": 60000}])
    assert pair.change_ms == -1000
    assert pair.spread_ms is None
