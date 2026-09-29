from ac_race_engineer.telemetry.assetto_corsa.comparison import (
    LapComparison,
    SectorDelta,
)
from ac_race_engineer.telemetry.assetto_corsa.diagnostics import (
    AssettoCorsaDiagnosticService,
)


def build_comparison() -> LapComparison:
    return LapComparison(
        session_id="session-001",
        reference_lap_number=2,
        target_lap_number=5,
        reference_lap_time_ms=104000,
        target_lap_time_ms=104154,
        total_delta_ms=154,
        sectors=(
            SectorDelta(
                sector_number=1,
                reference_time_ms=34000,
                target_time_ms=33769,
                delta_ms=-231,
            ),
            SectorDelta(
                sector_number=2,
                reference_time_ms=37000,
                target_time_ms=37487,
                delta_ms=487,
            ),
            SectorDelta(
                sector_number=3,
                reference_time_ms=33000,
                target_time_ms=32898,
                delta_ms=-102,
            ),
        ),
        sector_delta_total_ms=154,
        time_gained_ms=333,
        time_lost_ms=487,
        biggest_gain_sector=1,
        biggest_loss_sector=2,
        complete_sector_comparison=True,
    )


def test_detects_target_is_slower() -> None:
    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        build_comparison()
    )

    assert diagnosis.target_is_slower
    assert not diagnosis.target_is_faster
    assert not diagnosis.target_is_equal


def test_detects_primary_loss() -> None:
    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        build_comparison()
    )

    assert (
        diagnosis.primary_loss_sector
        == 2
    )

    assert (
        diagnosis.primary_loss_ms
        == 487
    )


def test_calculates_primary_loss_share() -> None:
    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        build_comparison()
    )

    assert (
        diagnosis.primary_loss_share
        == 1.0
    )


def test_detects_primary_gain() -> None:
    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        build_comparison()
    )

    assert (
        diagnosis.primary_gain_sector
        == 1
    )

    assert (
        diagnosis.primary_gain_ms
        == 231
    )


def test_orders_losses_from_biggest() -> None:
    comparison = LapComparison(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        reference_lap_time_ms=100000,
        target_lap_time_ms=100600,
        total_delta_ms=600,
        sectors=(
            SectorDelta(
                sector_number=1,
                reference_time_ms=30000,
                target_time_ms=30200,
                delta_ms=200,
            ),
            SectorDelta(
                sector_number=2,
                reference_time_ms=30000,
                target_time_ms=30500,
                delta_ms=500,
            ),
            SectorDelta(
                sector_number=3,
                reference_time_ms=40000,
                target_time_ms=39900,
                delta_ms=-100,
            ),
        ),
        sector_delta_total_ms=600,
        time_gained_ms=100,
        time_lost_ms=700,
        biggest_gain_sector=3,
        biggest_loss_sector=2,
        complete_sector_comparison=True,
    )

    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        comparison
    )

    assert [
        sector.sector_number
        for sector in diagnosis.lost_sectors
    ] == [
        2,
        1,
    ]


def test_orders_gains_from_biggest() -> None:
    comparison = LapComparison(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        reference_lap_time_ms=100000,
        target_lap_time_ms=99500,
        total_delta_ms=-500,
        sectors=(
            SectorDelta(
                sector_number=1,
                reference_time_ms=30000,
                target_time_ms=29800,
                delta_ms=-200,
            ),
            SectorDelta(
                sector_number=2,
                reference_time_ms=30000,
                target_time_ms=30100,
                delta_ms=100,
            ),
            SectorDelta(
                sector_number=3,
                reference_time_ms=40000,
                target_time_ms=39600,
                delta_ms=-400,
            ),
        ),
        sector_delta_total_ms=-500,
        time_gained_ms=600,
        time_lost_ms=100,
        biggest_gain_sector=3,
        biggest_loss_sector=2,
        complete_sector_comparison=True,
    )

    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        comparison
    )

    assert [
        sector.sector_number
        for sector in diagnosis.gained_sectors
    ] == [
        3,
        1,
    ]


def test_detects_neutral_sector() -> None:
    comparison = LapComparison(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        reference_lap_time_ms=100000,
        target_lap_time_ms=100000,
        total_delta_ms=0,
        sectors=(
            SectorDelta(
                sector_number=1,
                reference_time_ms=30000,
                target_time_ms=30000,
                delta_ms=0,
            ),
        ),
        sector_delta_total_ms=0,
        time_gained_ms=0,
        time_lost_ms=0,
        biggest_gain_sector=None,
        biggest_loss_sector=None,
        complete_sector_comparison=True,
    )

    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        comparison
    )

    assert diagnosis.target_is_equal

    assert (
        diagnosis.neutral_sectors
        == (1,)
    )


def test_detects_unexplained_delta() -> None:
    comparison = LapComparison(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        reference_lap_time_ms=100000,
        target_lap_time_ms=100500,
        total_delta_ms=500,
        sectors=(
            SectorDelta(
                sector_number=1,
                reference_time_ms=30000,
                target_time_ms=30200,
                delta_ms=200,
            ),
        ),
        sector_delta_total_ms=200,
        time_gained_ms=0,
        time_lost_ms=200,
        biggest_gain_sector=None,
        biggest_loss_sector=1,
        complete_sector_comparison=False,
    )

    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        comparison
    )

    assert (
        diagnosis.unexplained_delta_ms
        == 300
    )

    assert (
        diagnosis.sector_delta_matches_lap_delta
        is False
    )

    assert (
        diagnosis.complete_sector_data
        is False
    )


def test_no_sector_data_is_not_actionable() -> None:
    comparison = LapComparison(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        reference_lap_time_ms=100000,
        target_lap_time_ms=101000,
        total_delta_ms=1000,
        sectors=(),
        sector_delta_total_ms=0,
        time_gained_ms=0,
        time_lost_ms=0,
        biggest_gain_sector=None,
        biggest_loss_sector=None,
        complete_sector_comparison=False,
    )

    service = (
        AssettoCorsaDiagnosticService()
    )

    diagnosis = service.diagnose(
        comparison
    )

    assert (
        diagnosis.has_actionable_sector_data
        is False
    )

    assert (
        diagnosis.primary_loss_sector
        is None
    )