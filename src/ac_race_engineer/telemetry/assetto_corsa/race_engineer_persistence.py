from dataclasses import fields, is_dataclass
from enum import Enum
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from ac_race_engineer.database.race_engineer_analyses import (
    RaceEngineerAnalysisRecord,
)
from ac_race_engineer.database.repositories.race_engineer_analyses import (
    RaceEngineerAnalysisRepository,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_pipeline import (
    RaceEngineerPipelineResult,
)


def _to_json_value(
    value: object,
) -> object:
    if isinstance(
        value,
        Enum,
    ):
        return value.value

    if is_dataclass(
        value
    ):
        return {
            field.name: _to_json_value(
                getattr(
                    value,
                    field.name,
                )
            )
            for field in fields(
                value
            )
        }

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _to_json_value(
                item
            )
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (tuple, list),
    ):
        return [
            _to_json_value(
                item
            )
            for item in value
        ]

    return value


class AssettoCorsaRaceEngineerPersistenceService:
    """
    Persist one completed Race Engineer pipeline result.

    The structured report remains the source of truth.

    Frequently queried values are duplicated into
    dedicated SQL columns for efficient filtering and
    analytics.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.repository = (
            RaceEngineerAnalysisRepository(
                session
            )
        )

    def save(
        self,
        result: RaceEngineerPipelineResult,
        *,
        session_id: str | None = None,
        analysis_id: str | None = None,
    ) -> RaceEngineerAnalysisRecord:
        normalized_session_id = (
            None
            if session_id is None
            else session_id.strip()
        )

        if (
            session_id is not None
            and not normalized_session_id
        ):
            raise ValueError(
                "session_id cannot be empty"
            )

        normalized_analysis_id = (
            analysis_id
            or str(
                uuid4()
            )
        )

        if not normalized_analysis_id.strip():
            raise ValueError(
                "analysis_id cannot be empty"
            )

        report = result.report

        report_json = _to_json_value(
            report
        )

        if not isinstance(
            report_json,
            dict,
        ):
            raise TypeError(
                "Race Engineer report must "
                "serialize to a dictionary"
            )

        explanation_json = None

        if result.explanation is not None:
            serialized_explanation = (
                _to_json_value(
                    result.explanation
                )
            )

            if not isinstance(
                serialized_explanation,
                dict,
            ):
                raise TypeError(
                    "Race Engineer explanation "
                    "must serialize to a dictionary"
                )

            explanation_json = (
                serialized_explanation
            )

        return self.repository.save(
            analysis_id=(
                normalized_analysis_id
            ),
            session_id=(
                normalized_session_id
            ),
            reference_lap_number=(
                report.reference_lap_number
            ),
            target_lap_number=(
                report.target_lap_number
            ),
            trend=report.trend.value,
            total_time_lost_seconds=(
                report.total_time_lost_seconds
            ),
            total_time_gained_seconds=(
                report.total_time_gained_seconds
            ),
            net_time_delta_seconds=(
                report.net_time_delta_seconds
            ),
            primary_problem_corner=(
                report.primary_problem_corner
            ),
            recommendations_generated=(
                report.recommendations_generated
            ),
            recommendations_selected=(
                report.recommendations_selected
            ),
            recommendations_suppressed=(
                report
                .recommendations_suppressed
            ),
            report_json=report_json,
            explanation_json=(
                explanation_json
            ),
        )


class AssettoCorsaRaceEngineerPersistenceManager:
    """
    Transaction-owning persistence adapter.

    Suitable for application and API usage.

    Each operation creates its own SQLAlchemy session.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = (
            session_factory
        )

    def save(
        self,
        result: RaceEngineerPipelineResult,
        *,
        session_id: str | None = None,
        analysis_id: str | None = None,
    ) -> RaceEngineerAnalysisRecord:
        with self._session_factory() as session:
            try:
                service = (
                    AssettoCorsaRaceEngineerPersistenceService(
                        session
                    )
                )

                record = service.save(
                    result,
                    session_id=session_id,
                    analysis_id=analysis_id,
                )

                session.commit()

                return record

            except Exception:
                session.rollback()
                raise

    def get_by_id(
        self,
        analysis_id: str,
    ) -> RaceEngineerAnalysisRecord | None:
        with self._session_factory() as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            return repository.get_by_id(
                analysis_id
            )

    def list_recent(
        self,
        *,
        limit: int = 20,
    ) -> list[
        RaceEngineerAnalysisRecord
    ]:
        with self._session_factory() as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            return repository.list_recent(
                limit=limit
            )

    def list_for_session(
        self,
        session_id: str,
    ) -> list[
        RaceEngineerAnalysisRecord
    ]:
        normalized_session_id = (
            session_id.strip()
        )

        if not normalized_session_id:
            raise ValueError(
                "session_id cannot be empty"
            )

        with self._session_factory() as session:
            repository = (
                RaceEngineerAnalysisRepository(
                    session
                )
            )

            return repository.list_for_session(
                normalized_session_id
            )