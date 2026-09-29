from ac_race_engineer.telemetry.assetto_corsa.diagnostics import (
    LapComparisonDiagnosis,
    SectorImpact,
)
from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    AssettoCorsaRecommendationService,
    RecommendationPriority,
    RecommendationType,
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
            SectorImpact(
                sector_number=3,
                delta_ms=-102,
            ),
        ),
        neutral_sectors=(),
        complete_sector_data=True,
        sector_delta_matches_lap_delta=True,
        unexplained_delta_ms=0,
        has_actionable_sector_data=True,
    )


def test_primary_loss_becomes_high_priority() -> None:
    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        build_diagnosis()
    )

    primary = next(
        recommendation
        for recommendation
        in result.recommendations
        if (
            recommendation.recommendation_type
            == RecommendationType.PRIMARY_SECTOR
        )
    )

    assert (
        primary.priority
        == RecommendationPriority.HIGH
    )

    assert (
        primary.sector_number
        == 2
    )


def test_primary_recommendation_contains_evidence() -> None:
    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        build_diagnosis()
    )

    primary = next(
        recommendation
        for recommendation
        in result.recommendations
        if (
            recommendation.recommendation_type
            == RecommendationType.PRIMARY_SECTOR
        )
    )

    assert len(
        primary.evidence
    ) == 2

    assert any(
        "0.487 s"
        in evidence
        for evidence in primary.evidence
    )


def test_gain_creates_preserve_recommendation() -> None:
    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        build_diagnosis()
    )

    gain = next(
        recommendation
        for recommendation
        in result.recommendations
        if (
            recommendation.recommendation_type
            == RecommendationType.CONSOLIDATE_GAIN
        )
    )

    assert (
        gain.priority
        == RecommendationPriority.LOW
    )

    assert (
        gain.sector_number
        == 1
    )


def test_incomplete_data_creates_warning() -> None:
    diagnosis = build_diagnosis()

    diagnosis = LapComparisonDiagnosis(
        session_id=diagnosis.session_id,
        reference_lap_number=(
            diagnosis.reference_lap_number
        ),
        target_lap_number=(
            diagnosis.target_lap_number
        ),
        total_delta_ms=500,
        target_is_faster=False,
        target_is_slower=True,
        target_is_equal=False,
        time_gained_ms=0,
        time_lost_ms=200,
        primary_loss_sector=1,
        primary_loss_ms=200,
        primary_loss_share=1.0,
        primary_gain_sector=None,
        primary_gain_ms=0,
        lost_sectors=(
            SectorImpact(
                sector_number=1,
                delta_ms=200,
            ),
        ),
        gained_sectors=(),
        neutral_sectors=(),
        complete_sector_data=False,
        sector_delta_matches_lap_delta=False,
        unexplained_delta_ms=300,
        has_actionable_sector_data=True,
    )

    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        diagnosis
    )

    assert (
        result.recommendations[0].recommendation_type
        == RecommendationType.DATA_QUALITY
    )

    assert (
        result.recommendations[0].priority
        == RecommendationPriority.HIGH
    )


def test_multiple_losses_create_secondary_priority() -> None:
    diagnosis = LapComparisonDiagnosis(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        total_delta_ms=600,
        target_is_faster=False,
        target_is_slower=True,
        target_is_equal=False,
        time_gained_ms=100,
        time_lost_ms=700,
        primary_loss_sector=2,
        primary_loss_ms=500,
        primary_loss_share=(
            500 / 700
        ),
        primary_gain_sector=3,
        primary_gain_ms=100,
        lost_sectors=(
            SectorImpact(
                sector_number=2,
                delta_ms=500,
            ),
            SectorImpact(
                sector_number=1,
                delta_ms=200,
            ),
        ),
        gained_sectors=(
            SectorImpact(
                sector_number=3,
                delta_ms=-100,
            ),
        ),
        neutral_sectors=(),
        complete_sector_data=True,
        sector_delta_matches_lap_delta=True,
        unexplained_delta_ms=0,
        has_actionable_sector_data=True,
    )

    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        diagnosis
    )

    secondary = next(
        recommendation
        for recommendation
        in result.recommendations
        if (
            recommendation.recommendation_type
            == RecommendationType.SECONDARY_SECTOR
        )
    )

    assert (
        secondary.sector_number
        == 1
    )

    assert (
        secondary.priority
        == RecommendationPriority.MEDIUM
    )


def test_distributed_losses_create_balanced_recommendation() -> None:
    diagnosis = LapComparisonDiagnosis(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        total_delta_ms=600,
        target_is_faster=False,
        target_is_slower=True,
        target_is_equal=False,
        time_gained_ms=0,
        time_lost_ms=600,
        primary_loss_sector=1,
        primary_loss_ms=250,
        primary_loss_share=(
            250 / 600
        ),
        primary_gain_sector=None,
        primary_gain_ms=0,
        lost_sectors=(
            SectorImpact(
                sector_number=1,
                delta_ms=250,
            ),
            SectorImpact(
                sector_number=2,
                delta_ms=200,
            ),
            SectorImpact(
                sector_number=3,
                delta_ms=150,
            ),
        ),
        gained_sectors=(),
        neutral_sectors=(),
        complete_sector_data=True,
        sector_delta_matches_lap_delta=True,
        unexplained_delta_ms=0,
        has_actionable_sector_data=True,
    )

    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        diagnosis
    )

    balanced = next(
        recommendation
        for recommendation
        in result.recommendations
        if (
            recommendation.recommendation_type
            == RecommendationType.BALANCED_IMPROVEMENT
        )
    )

    assert (
        balanced.priority
        == RecommendationPriority.MEDIUM
    )


def test_no_actionable_data_generates_no_timing_recommendations() -> None:
    diagnosis = LapComparisonDiagnosis(
        session_id="session-001",
        reference_lap_number=1,
        target_lap_number=2,
        total_delta_ms=1000,
        target_is_faster=False,
        target_is_slower=True,
        target_is_equal=False,
        time_gained_ms=0,
        time_lost_ms=0,
        primary_loss_sector=None,
        primary_loss_ms=0,
        primary_loss_share=None,
        primary_gain_sector=None,
        primary_gain_ms=0,
        lost_sectors=(),
        gained_sectors=(),
        neutral_sectors=(),
        complete_sector_data=False,
        sector_delta_matches_lap_delta=False,
        unexplained_delta_ms=1000,
        has_actionable_sector_data=False,
    )

    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        diagnosis
    )

    assert len(
        result.recommendations
    ) == 1

    assert (
        result.recommendations[
            0
        ].recommendation_type
        == RecommendationType.DATA_QUALITY
    )


def test_recommendations_are_sorted_by_priority() -> None:
    service = (
        AssettoCorsaRecommendationService()
    )

    result = service.generate(
        build_diagnosis()
    )

    priorities = [
        recommendation.priority
        for recommendation
        in result.recommendations
    ]

    assert priorities == [
        RecommendationPriority.HIGH,
        RecommendationPriority.LOW,
    ]