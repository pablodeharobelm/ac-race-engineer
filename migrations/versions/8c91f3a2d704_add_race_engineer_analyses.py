"""add race engineer analyses

Revision ID: 8c91f3a2d704
Revises: b2fa323089d0
Create Date: 2026-10-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c91f3a2d704"

down_revision: (
    str
    | Sequence[str]
    | None
) = "b2fa323089d0"

branch_labels: (
    str
    | Sequence[str]
    | None
) = None

depends_on: (
    str
    | Sequence[str]
    | None
) = None


def upgrade() -> None:
    op.create_table(
        "race_engineer_analyses",
        sa.Column(
            "id",
            sa.String(
                length=64
            ),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(
                length=64
            ),
            nullable=True,
        ),
        sa.Column(
            "reference_lap_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "target_lap_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "trend",
            sa.String(
                length=32
            ),
            nullable=False,
        ),
        sa.Column(
            "total_time_lost_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "total_time_gained_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "net_time_delta_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "primary_problem_corner",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "recommendations_generated",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "recommendations_selected",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "recommendations_suppressed",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "report_json",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "explanation_json",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=sa.text(
                "now()"
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        "ix_race_engineer_analyses_session_id",
        "race_engineer_analyses",
        [
            "session_id",
        ],
        unique=False,
    )

    op.create_index(
        "ix_race_engineer_analyses_created_at",
        "race_engineer_analyses",
        [
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_race_engineer_analyses_created_at",
        table_name=(
            "race_engineer_analyses"
        ),
    )

    op.drop_index(
        "ix_race_engineer_analyses_session_id",
        table_name=(
            "race_engineer_analyses"
        ),
    )

    op.drop_table(
        "race_engineer_analyses"
    )