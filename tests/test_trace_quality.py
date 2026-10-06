import pytest

from ac_race_engineer.dashboard.trace_quality import trace_quality


def test_coverage_does_not_hide_gaps_or_partial_overlap():
    reference = [{"progress": p} for p in (0.0, 0.1, 0.8, 0.95)]
    target = [{"progress": p} for p in (0.2, 0.4, 1.0)]
    quality = trace_quality(reference, target)
    assert quality["shared_start"] == 0.2
    assert quality["shared_end"] == 0.95
    assert quality["shared_span"] == pytest.approx(0.75)
    assert quality["reference"]["samples"] == 4
    assert quality["reference"]["largest_gap"] == pytest.approx(0.7)
    assert quality["reference"]["gap_start"] == 0.1
    assert quality["reference"]["gap_end"] == 0.8


def test_disjoint_traces_have_no_shared_span():
    quality = trace_quality([{"progress": 0}, {"progress": 0.2}], [{"progress": 0.5}, {"progress": 1}])
    assert quality["shared_span"] == 0
