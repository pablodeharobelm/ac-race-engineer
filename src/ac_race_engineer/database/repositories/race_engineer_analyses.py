from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from ac_race_engineer.database.race_engineer_analyses import (
    RaceEngineerAnalysisRecord,
    race_engineer_analyses_table,
)


class RaceEngineerAnalysisRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    @staticmethod
    def _to_record(
        row,
    ) -> RaceEngineerAnalysisRecord:
        return RaceEngineerAnalysisRecord(
            id=row["id"],
            session_id=row["session_id"],
            reference_lap_number=(
                row["reference_lap_number"]
            ),
            target_lap_number=(
                row["target_lap_number"]
            ),
            trend=row["trend"],
            total_time_lost_seconds=(
                row["total_time_lost_seconds"]
            ),
            total_time_gained_seconds=(
                row["total_time_gained_seconds"]
            ),
            net_time_delta_seconds=(
                row["net_time_delta_seconds"]
            ),
            primary_problem_corner=(
                row["primary_problem_corner"]
            ),
            recommendations_generated=(
                row["recommendations_generated"]
            ),
            recommendations_selected=(
                row["recommendations_selected"]
            ),
            recommendations_suppressed=(
                row["recommendations_suppressed"]
            ),
            report_json=row["report_json"],
            explanation_json=(
                row["explanation_json"]
            ),
            created_at=row["created_at"],
        )

    def get_by_id(
        self,
        analysis_id: str,
    ) -> RaceEngineerAnalysisRecord | None:
        statement = (
            select(
                race_engineer_analyses_table
            )
            .where(
                race_engineer_analyses_table.c.id
                == analysis_id
            )
        )

        row = (
            self._session.execute(
                statement
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        return self._to_record(
            row
        )

    def list_for_session(
        self,
        session_id: str,
    ) -> list[
        RaceEngineerAnalysisRecord
    ]:
        statement = (
            select(
                race_engineer_analyses_table
            )
            .where(
                race_engineer_analyses_table
                .c.session_id
                == session_id
            )
            .order_by(
                race_engineer_analyses_table
                .c.created_at.desc(),
                race_engineer_analyses_table
                .c.id.desc(),
            )
        )

        rows = (
            self._session.execute(
                statement
            )
            .mappings()
            .all()
        )

        return [
            self._to_record(
                row
            )
            for row in rows
        ]

    def list_recent(
        self,
        *,
        limit: int = 20,
    ) -> list[
        RaceEngineerAnalysisRecord
    ]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than 0"
            )

        statement = (
            select(
                race_engineer_analyses_table
            )
            .order_by(
                race_engineer_analyses_table
                .c.created_at.desc(),
                race_engineer_analyses_table
                .c.id.desc(),
            )
            .limit(
                limit
            )
        )

        rows = (
            self._session.execute(
                statement
            )
            .mappings()
            .all()
        )

        return [
            self._to_record(
                row
            )
            for row in rows
        ]

    def save(
        self,
        *,
        analysis_id: str,
        session_id: str | None,
        reference_lap_number: int,
        target_lap_number: int,
        trend: str,
        total_time_lost_seconds: float,
        total_time_gained_seconds: float,
        net_time_delta_seconds: float,
        primary_problem_corner: int | None,
        recommendations_generated: int,
        recommendations_selected: int,
        recommendations_suppressed: int,
        report_json: dict,
        explanation_json: dict | None,
    ) -> RaceEngineerAnalysisRecord:
        statement = insert(
            race_engineer_analyses_table
        ).values(
            id=analysis_id,
            session_id=session_id,
            reference_lap_number=(
                reference_lap_number
            ),
            target_lap_number=(
                target_lap_number
            ),
            trend=trend,
            total_time_lost_seconds=(
                total_time_lost_seconds
            ),
            total_time_gained_seconds=(
                total_time_gained_seconds
            ),
            net_time_delta_seconds=(
                net_time_delta_seconds
            ),
            primary_problem_corner=(
                primary_problem_corner
            ),
            recommendations_generated=(
                recommendations_generated
            ),
            recommendations_selected=(
                recommendations_selected
            ),
            recommendations_suppressed=(
                recommendations_suppressed
            ),
            report_json=report_json,
            explanation_json=(
                explanation_json
            ),
        )

        self._session.execute(
            statement
        )

        self._session.flush()

        record = self.get_by_id(
            analysis_id
        )

        if record is None:
            raise RuntimeError(
                "Race Engineer analysis "
                "was not persisted"
            )

        return record