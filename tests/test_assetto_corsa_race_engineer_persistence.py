from types import SimpleNamespace

import pytest

from ac_race_engineer.database.race_engineer_analyses import (
    race_engineer_analysis_metadata,
)
from ac_race_engineer.database.repositories.race_engineer_analyses import (
    RaceEngineerAnalysisRepository,
)
from ac_race_engineer.database.session import (
    create_database_engine,
    create_session_factory,
    database_session,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_persistence import (
    AssettoCorsaRaceEngineerPersistenceManager,
    AssettoCorsaRaceEngineerPersistenceService,
)
from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    CoachingFocusLevel,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendationType,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_llm import (
    RaceEngineerExplanation,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    RaceEngineerCornerSummary,
    RaceEngineerFocusSummary,
    RaceEngineerReport,
    RaceEngineerTrend,
)


def report() -> RaceEngineerReport:
    return RaceEngineerReport(
        reference_lap_number=2,
        target_lap_number=5,
        trend=(
            RaceEngineerTrend.LOSING_TIME
        ),
        total_time_lost_seconds=0.35,
        total_time_gained_seconds=0.10,
        net_time_delta_seconds=0.25,
        corners_analyzed=1,
        corners_with_time_loss=1,
        corners_with_issues=1,
        recommendations_generated=3,
        recommendations_selected=2,
        recommendations_suppressed=1,
        primary_problem_corner=1,
        corners=(
            RaceEngineerCornerSummary(
                corner_number=1,
                time_lost_seconds=0.35,
                time_gained_seconds=0.0,
                entry_time_loss_seconds=0.20,
                exit_time_loss_seconds=0.15,
                dominant_phase=(
                    DrivingPhase.ENTRY
                ),
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
                issue_count=3,
            ),
        ),
        focuses=(
            RaceEngineerFocusSummary(
                rank=1,
                focus_level=(
                    CoachingFocusLevel.PRIMARY
                ),
                corner_number=1,
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKING_POINT
                ),
                priority=(
                    RecommendationPriority.HIGH
                ),
                phase=DrivingPhase.ENTRY,
                title="Brake slightly later",
                instruction=(
                    "Move the braking point "
                    "slightly later."
                ),
                rationale=(
                    "The target brakes earlier."
                ),
                diagnostic_code=(
                    "BRAKING_TOO_EARLY"
                ),
                corner_time_loss_seconds=0.35,
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
            ),
        ),
    )


def pipeline_result(
    *,
    with_explanation: bool = False,
):
    explanation = None

    if with_explanation:
        explanation = RaceEngineerExplanation(
            reference_lap_number=2,
            target_lap_number=5,
            language="es",
            text=(
                "Trabaja primero la frenada "
                "de la curva 1."
            ),
            recommendation_count=2,
            corner_count=1,
        )

    return SimpleNamespace(
        report=report(),
        explanation=explanation,
    )


def create_engine_with_schema():
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    race_engineer_analysis_metadata.create_all(
        engine
    )

    return engine


def test_persists_analysis() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            record = service.save(
                pipeline_result(),
                session_id="session-001",
                analysis_id="analysis-001",
            )

            assert (
                record.id
                == "analysis-001"
            )

            assert (
                record.session_id
                == "session-001"
            )

            assert (
                record.reference_lap_number
                == 2
            )

            assert (
                record.target_lap_number
                == 5
            )

            assert (
                record.trend
                == "losing_time"
            )

            assert (
                record.net_time_delta_seconds
                == pytest.approx(
                    0.25
                )
            )

            assert (
                record.primary_problem_corner
                == 1
            )

    finally:
        engine.dispose()


def test_persists_full_report_json() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            record = service.save(
                pipeline_result(),
                analysis_id="analysis-json",
            )

            assert (
                record.report_json[
                    "reference_lap_number"
                ]
                == 2
            )

            assert (
                record.report_json[
                    "trend"
                ]
                == "losing_time"
            )

            assert (
                record.report_json[
                    "corners"
                ][0][
                    "dominant_phase"
                ]
                == "ENTRY"
            )

            assert (
                record.report_json[
                    "focuses"
                ][0][
                    "priority"
                ]
                == "high"
            )

            assert (
                record.report_json[
                    "focuses"
                ][0][
                    "diagnostic_code"
                ]
                == "BRAKING_TOO_EARLY"
            )

    finally:
        engine.dispose()


def test_persists_optional_explanation() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            record = service.save(
                pipeline_result(
                    with_explanation=True
                ),
                analysis_id="analysis-llm",
            )

            assert (
                record.explanation_json
                is not None
            )

            assert (
                record.explanation_json[
                    "language"
                ]
                == "es"
            )

            assert (
                "curva 1"
                in record.explanation_json[
                    "text"
                ]
            )

    finally:
        engine.dispose()


def test_supports_analysis_without_explanation() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            record = service.save(
                pipeline_result(),
            )

            assert (
                record.id
            )

            assert (
                record.explanation_json
                is None
            )

    finally:
        engine.dispose()


def test_repository_get_by_id() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            service.save(
                pipeline_result(),
                analysis_id="analysis-find",
            )

        with database_session(
            engine
        ) as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            record = repository.get_by_id(
                "analysis-find"
            )

            assert record is not None

            assert (
                record.target_lap_number
                == 5
            )

    finally:
        engine.dispose()


def test_repository_lists_session_history() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            service.save(
                pipeline_result(),
                session_id="session-a",
                analysis_id="analysis-a1",
            )

            service.save(
                pipeline_result(),
                session_id="session-a",
                analysis_id="analysis-a2",
            )

            service.save(
                pipeline_result(),
                session_id="session-b",
                analysis_id="analysis-b1",
            )

        with database_session(
            engine
        ) as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            records = (
                repository.list_for_session(
                    "session-a"
                )
            )

            assert len(
                records
            ) == 2

            assert {
                record.id
                for record in records
            } == {
                "analysis-a1",
                "analysis-a2",
            }

    finally:
        engine.dispose()


def test_repository_lists_recent() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            for number in range(
                3
            ):
                service.save(
                    pipeline_result(),
                    analysis_id=(
                        f"analysis-{number}"
                    ),
                )

        with database_session(
            engine
        ) as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            records = (
                repository.list_recent(
                    limit=2
                )
            )

            assert len(
                records
            ) == 2

    finally:
        engine.dispose()


def test_repository_rejects_invalid_limit() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            with pytest.raises(
                ValueError,
                match="limit",
            ):
                repository.list_recent(
                    limit=0
                )

    finally:
        engine.dispose()


def test_rejects_empty_session_id() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        with database_session(
            engine
        ) as session:
            service = (
                AssettoCorsaRaceEngineerPersistenceService(
                    session
                )
            )

            with pytest.raises(
                ValueError,
                match="session_id",
            ):
                service.save(
                    pipeline_result(),
                    session_id="   ",
                )

    finally:
        engine.dispose()


def test_manager_owns_transaction() -> None:
    engine = (
        create_engine_with_schema()
    )

    try:
        session_factory = (
            create_session_factory(
                engine
            )
        )

        manager = (
            AssettoCorsaRaceEngineerPersistenceManager(
                session_factory
            )
        )

        saved = manager.save(
            pipeline_result(),
            session_id="session-manager",
            analysis_id="analysis-manager",
        )

        assert (
            saved.id
            == "analysis-manager"
        )

        with database_session(
            engine
        ) as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            restored = (
                repository.get_by_id(
                    "analysis-manager"
                )
            )

            assert restored is not None

            assert (
                restored.session_id
                == "session-manager"
            )

    finally:
        engine.dispose()