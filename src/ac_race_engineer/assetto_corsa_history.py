import argparse
from collections.abc import Sequence

from ac_race_engineer.database.repositories.sessions import (
    SessionRepository,
)
from ac_race_engineer.database.session import (
    create_database_engine,
    database_session,
)
from ac_race_engineer.telemetry.assetto_corsa.comparison import (
    AssettoCorsaLapComparisonService,
    LapComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.diagnostics import (
    AssettoCorsaDiagnosticService,
    LapComparisonDiagnosis,
)
from ac_race_engineer.telemetry.assetto_corsa.history import (
    AssettoCorsaHistoryService,
    SessionPerformanceSummary,
    format_time_ms,
)
from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    AssettoCorsaRecommendationService,
    RaceEngineerRecommendationSet,
)


def _positive_int(
    value: str,
) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "lap number must be greater than 0"
        )

    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect persisted Assetto Corsa "
            "session performance"
        )
    )

    session_group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    session_group.add_argument(
        "--latest",
        action="store_true",
        help=(
            "Show the latest persisted "
            "Assetto Corsa session"
        ),
    )

    session_group.add_argument(
        "--session",
        type=str,
        help=(
            "Show a specific session "
            "by session ID"
        ),
    )

    parser.add_argument(
        "--laps",
        action="store_true",
        help="Show lap-by-lap details",
    )

    parser.add_argument(
        "--sectors",
        action="store_true",
        help=(
            "Show sectors for each lap"
        ),
    )

    comparison_group = (
        parser.add_mutually_exclusive_group()
    )

    comparison_group.add_argument(
        "--compare",
        nargs=2,
        type=_positive_int,
        metavar=(
            "REFERENCE_LAP",
            "TARGET_LAP",
        ),
        help=(
            "Compare two laps. "
            "Delta is target minus reference."
        ),
    )

    comparison_group.add_argument(
        "--compare-best",
        type=_positive_int,
        metavar="LAP",
        help=(
            "Compare a lap against "
            "the session best lap"
        ),
    )

    parser.add_argument(
        "--engineer",
        action="store_true",
        help=(
            "Generate deterministic Race Engineer "
            "diagnosis and recommendations. "
            "Requires --compare or --compare-best."
        ),
    )

    return parser


def _format_delta_ms(
    milliseconds: float | None,
) -> str:
    if milliseconds is None:
        return "--"

    return (
        f"{milliseconds / 1000.0:.3f} s"
    )


def _format_signed_delta_ms(
    milliseconds: float,
) -> str:
    return (
        f"{milliseconds / 1000.0:+.3f} s"
    )


def _session_type_label(
    session_type: str,
) -> str:
    return (
        session_type
        .replace("_", " ")
        .title()
    )


def _print_header(
    summary: SessionPerformanceSummary,
) -> None:
    print()
    print("=" * 64)
    print(
        "AC Race Engineer - Session Analysis"
    )
    print("=" * 64)

    print(
        f"Session: {summary.session_id}"
    )

    print(
        f"Car:     {summary.car_key}"
    )

    print(
        f"Track:   {summary.track_key}"
    )

    print(
        "Type:    "
        f"{_session_type_label(summary.session_type)}"
    )

    print(
        f"Source:  {summary.source}"
    )


def _print_performance(
    summary: SessionPerformanceSummary,
) -> None:
    print()
    print("Performance")
    print("-" * 64)

    print(
        f"Laps:          "
        f"{summary.lap_count}"
    )

    print(
        "Best lap:      "
        f"{format_time_ms(summary.best_lap_time_ms)}"
    )

    if (
        summary.best_lap_number
        is not None
    ):
        print(
            "Best lap no.:  "
            f"{summary.best_lap_number}"
        )

    print(
        "Average:       "
        f"{format_time_ms(summary.average_lap_time_ms)}"
    )

    print(
        "Consistency:   "
        f"{_format_delta_ms(summary.consistency_stddev_ms)}"
    )

    print(
        "Theoretical:   "
        f"{format_time_ms(summary.theoretical_best_lap_ms)}"
    )

    print(
        "Potential:     "
        f"{_format_delta_ms(summary.potential_gain_ms)}"
    )


def _print_best_sectors(
    summary: SessionPerformanceSummary,
) -> None:
    if not summary.best_sectors:
        return

    print()
    print("Best sectors")
    print("-" * 64)

    for sector in summary.best_sectors:
        print(
            f"S{sector.sector_number}: "
            f"{format_time_ms(sector.sector_time_ms)}"
        )


def _print_laps(
    summary: SessionPerformanceSummary,
    *,
    show_sectors: bool,
) -> None:
    if not summary.laps:
        print()
        print(
            "No completed laps stored."
        )
        return

    print()
    print("Laps")
    print("-" * 64)

    best_time = (
        summary.best_lap_time_ms
    )

    for lap in summary.laps:
        delta = None

        if (
            best_time is not None
            and lap.lap_time_ms > 0
        ):
            delta = (
                lap.lap_time_ms
                - best_time
            )

        best_marker = (
            " BEST"
            if lap.is_session_best
            else ""
        )

        delta_text = ""

        if (
            delta is not None
            and delta > 0
        ):
            delta_text = (
                f"  +{delta / 1000.0:.3f}s"
            )

        print(
            f"Lap {lap.lap_number:>3}  "
            f"{format_time_ms(lap.lap_time_ms)}"
            f"{delta_text}"
            f"{best_marker}"
        )

        if show_sectors:
            for sector in lap.sectors:
                print(
                    "         "
                    f"S{sector.sector_number}: "
                    f"{format_time_ms(sector.sector_time_ms)}"
                )


def _print_comparison(
    comparison: LapComparison,
) -> None:
    print()
    print("Lap comparison")
    print("-" * 64)

    print(
        "Reference lap: "
        f"{comparison.reference_lap_number}  "
        f"{format_time_ms(comparison.reference_lap_time_ms)}"
    )

    print(
        "Target lap:    "
        f"{comparison.target_lap_number}  "
        f"{format_time_ms(comparison.target_lap_time_ms)}"
    )

    print(
        "Total delta:   "
        f"{_format_signed_delta_ms(comparison.total_delta_ms)}"
    )

    if comparison.sectors:
        print()
        print("Sector deltas")
        print("-" * 64)

        for sector in comparison.sectors:
            print(
                f"S{sector.sector_number:<2}  "
                f"{format_time_ms(sector.reference_time_ms)}"
                " -> "
                f"{format_time_ms(sector.target_time_ms)}"
                "   "
                f"{_format_signed_delta_ms(sector.delta_ms)}"
            )

    else:
        print()
        print(
            "No comparable sector data."
        )

    print()

    print(
        "Time gained:   "
        f"{comparison.time_gained_ms / 1000.0:.3f} s"
    )

    print(
        "Time lost:     "
        f"{comparison.time_lost_ms / 1000.0:.3f} s"
    )

    if (
        comparison.biggest_gain_sector
        is not None
    ):
        print(
            "Biggest gain: "
            f"S{comparison.biggest_gain_sector}"
        )

    if (
        comparison.biggest_loss_sector
        is not None
    ):
        print(
            "Biggest loss: "
            f"S{comparison.biggest_loss_sector}"
        )

    if (
        not comparison.complete_sector_comparison
    ):
        print()
        print(
            "WARNING: sector comparison is incomplete."
        )


def _print_diagnosis(
    diagnosis: LapComparisonDiagnosis,
) -> None:
    print()
    print("=" * 64)
    print("Race Engineer diagnosis")
    print("=" * 64)

    if diagnosis.target_is_faster:
        print(
            "Result: target lap is faster."
        )

    elif diagnosis.target_is_slower:
        print(
            "Result: target lap is slower."
        )

    else:
        print(
            "Result: both laps have the same time."
        )

    print(
        "Lap delta:       "
        f"{_format_signed_delta_ms(diagnosis.total_delta_ms)}"
    )

    print(
        "Measured gained: "
        f"{diagnosis.time_gained_ms / 1000.0:.3f} s"
    )

    print(
        "Measured lost:   "
        f"{diagnosis.time_lost_ms / 1000.0:.3f} s"
    )

    if (
        diagnosis.primary_loss_sector
        is not None
    ):
        print()
        print(
            "Primary loss:    "
            f"S{diagnosis.primary_loss_sector}"
        )

        print(
            "Primary loss:    "
            f"+{diagnosis.primary_loss_ms / 1000.0:.3f} s"
        )

        if (
            diagnosis.primary_loss_share
            is not None
        ):
            print(
                "Loss share:      "
                f"{diagnosis.primary_loss_share * 100.0:.1f}%"
            )

    if (
        diagnosis.primary_gain_sector
        is not None
    ):
        print()
        print(
            "Primary gain:    "
            f"S{diagnosis.primary_gain_sector}"
        )

        print(
            "Primary gain:    "
            f"-{diagnosis.primary_gain_ms / 1000.0:.3f} s"
        )

    if diagnosis.lost_sectors:
        print()
        print("Lost sectors")
        print("-" * 64)

        for sector in diagnosis.lost_sectors:
            print(
                f"S{sector.sector_number}: "
                f"+{sector.delta_ms / 1000.0:.3f} s"
            )

    if diagnosis.gained_sectors:
        print()
        print("Gained sectors")
        print("-" * 64)

        for sector in diagnosis.gained_sectors:
            print(
                f"S{sector.sector_number}: "
                f"{sector.delta_ms / 1000.0:.3f} s"
            )

    if not diagnosis.complete_sector_data:
        print()
        print(
            "WARNING: incomplete sector data."
        )

    if (
        not diagnosis.sector_delta_matches_lap_delta
    ):
        print(
            "WARNING: sectors do not fully "
            "explain the lap delta."
        )

        print(
            "Unexplained: "
            f"{_format_signed_delta_ms(diagnosis.unexplained_delta_ms)}"
        )


def _print_recommendations(
    recommendation_set: RaceEngineerRecommendationSet,
) -> None:
    print()
    print("=" * 64)
    print("Race Engineer priorities")
    print("=" * 64)

    if not recommendation_set.recommendations:
        print(
            "No timing recommendations available."
        )
        return

    for index, recommendation in enumerate(
        recommendation_set.recommendations,
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"[{recommendation.priority.value.upper()}] "
            f"{recommendation.title}"
        )

        print(
            f"   {recommendation.message}"
        )

        if recommendation.sector_number is not None:
            print(
                "   Sector: "
                f"S{recommendation.sector_number}"
            )

        if recommendation.evidence:
            print(
                "   Evidence:"
            )

            for evidence in recommendation.evidence:
                print(
                    f"   - {evidence}"
                )


def _print_summary(
    summary: SessionPerformanceSummary,
    *,
    show_laps: bool,
    show_sectors: bool,
) -> None:
    _print_header(
        summary
    )

    _print_performance(
        summary
    )

    _print_best_sectors(
        summary
    )

    if (
        show_laps
        or show_sectors
    ):
        _print_laps(
            summary,
            show_sectors=show_sectors,
        )


def _resolve_session_id(
    *,
    repository: SessionRepository,
    latest: bool,
    requested_session_id: str | None,
) -> str | None:
    if latest:
        record = repository.get_latest(
            source="assetto_corsa"
        )

        if record is None:
            return None

        return record.id

    return requested_session_id


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = _build_parser()

    args = parser.parse_args(
        argv
    )

    if (
        args.engineer
        and args.compare is None
        and args.compare_best is None
    ):
        parser.error(
            "--engineer requires "
            "--compare or --compare-best"
        )

    engine = (
        create_database_engine()
    )

    try:
        with database_session(
            engine
        ) as session:
            session_repository = (
                SessionRepository(
                    session
                )
            )

            session_id = (
                _resolve_session_id(
                    repository=(
                        session_repository
                    ),
                    latest=args.latest,
                    requested_session_id=(
                        args.session
                    ),
                )
            )

            if session_id is None:
                print(
                    "No Assetto Corsa "
                    "sessions found."
                )
                return 1

            history = (
                AssettoCorsaHistoryService(
                    session
                )
            )

            try:
                summary = (
                    history.get_summary(
                        session_id
                    )
                )

            except ValueError as exc:
                print(
                    str(exc)
                )
                return 2

            _print_summary(
                summary,
                show_laps=args.laps,
                show_sectors=args.sectors,
            )

            comparison_service = (
                AssettoCorsaLapComparisonService(
                    session
                )
            )

            comparison = None

            try:
                if args.compare is not None:
                    comparison = (
                        comparison_service.compare(
                            session_id=session_id,
                            reference_lap_number=(
                                args.compare[0]
                            ),
                            target_lap_number=(
                                args.compare[1]
                            ),
                        )
                    )

                elif (
                    args.compare_best
                    is not None
                ):
                    comparison = (
                        comparison_service.compare_to_best(
                            session_id=session_id,
                            lap_number=(
                                args.compare_best
                            ),
                        )
                    )

            except ValueError as exc:
                print()
                print(
                    f"Comparison error: {exc}"
                )
                return 3

            if comparison is not None:
                _print_comparison(
                    comparison
                )

            if (
                args.engineer
                and comparison is not None
            ):
                diagnostic_service = (
                    AssettoCorsaDiagnosticService()
                )

                diagnosis = (
                    diagnostic_service.diagnose(
                        comparison
                    )
                )

                _print_diagnosis(
                    diagnosis
                )

                recommendation_service = (
                    AssettoCorsaRecommendationService()
                )

                recommendations = (
                    recommendation_service.generate(
                        diagnosis
                    )
                )

                _print_recommendations(
                    recommendations
                )

            print()

    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )