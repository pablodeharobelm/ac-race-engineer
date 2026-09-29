import argparse

import pytest

from ac_race_engineer.assetto_corsa_history import (
    _format_signed_delta_ms,
    _positive_int,
    _print_diagnosis,
    _print_recommendations,
)
from ac_race_engineer.telemetry.assetto_corsa.diagnostics import (
    LapComparisonDiagnosis,
    SectorImpact,
)
from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RaceEngineerRecommendation,
    RaceEngineerRecommendationSet,
    RecommendationPriority,
    RecommendationType,
)


def test_formats_positive_delta() -> None:
    assert (
        _format_signed_delta_ms(
            487
        )
        == "+0.487 s"
    )


def test_formats_negative_delta() -> None:
    assert (
        _format_signed_delta_ms(
            -231
        )
        == "-0.231 s"
    )


def test_formats_zero_delta() -> None:
    assert (
        _format_signed_delta_ms(
            0
        )
        == "+0.000 s"
    )


def test_positive_lap_number() -> None:
    assert (
        _positive_int(
            "3"
        )
        == 3
    )


def test_invalid_lap_number() -> None:
    with pytest.raises(
        argparse.ArgumentTypeError
    ):
        _positive_int(
            "0"
        )


def test_negative_lap_number() -> None:
    with pytest.raises(
        argparse.ArgumentTypeError
    ):
        _positive_int(
            "-1"
        )


def build_diagnosis() -> LapComparisonDiagnosis:
    return LapComparisonDiagnosis(
        session_id="session-001",
        reference_lap_number=2,
        target_lap_number=5,
        total_delta_ms=154,
        target_is_faster=False,
        target_is_slower=True,
        target_is_equal=False,
        time_gained_ms=333,
        time_lost_ms=487,
        primary_loss_sector=2,
        primary_loss_ms=487,
        primary_loss_share=1.0,
        primary_gain_sector=1,
        primary_gain_ms=231,
        lost_sectors=(
            SectorImpact(
                sector_number=2,
                delta_ms=487,
            ),
        ),
        gained_sectors=(
            SectorImpact(
                sector_number=1,
                delta_ms=-231,
            ),
        ),
        neutral_sectors=(),
        complete_sector_data=True,
        sector_delta_matches_lap_delta=True,
        unexplained_delta_ms=0,
        has_actionable_sector_data=True,
    )


def test_print_diagnosis(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _print_diagnosis(
        build_diagnosis()
    )

    output = (
        capsys.readouterr().out
    )

    assert (
        "Race Engineer diagnosis"
        in output
    )

    assert "S2" in output
    assert "+0.487 s" in output
    assert "100.0%" in output


def test_print_recommendations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recommendation = (
        RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.PRIMARY_SECTOR
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            sector_number=2,
            title="Prioritize Sector 2",
            message=(
                "Sector 2 is the main loss."
            ),
            evidence=(
                "Time lost: 0.487 s",
            ),
        )
    )

    recommendation_set = (
        RaceEngineerRecommendationSet(
            session_id="session-001",
            reference_lap_number=2,
            target_lap_number=5,
            recommendations=(
                recommendation,
            ),
        )
    )

    _print_recommendations(
        recommendation_set
    )

    output = (
        capsys.readouterr().out
    )

    assert (
        "Race Engineer priorities"
        in output
    )

    assert "[HIGH]" in output

    assert (
        "Prioritize Sector 2"
        in output
    )

    assert (
        "Time lost: 0.487 s"
        in output
    )