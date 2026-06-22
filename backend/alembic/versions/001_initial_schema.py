"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. teams
    # ------------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("country_code", sa.CHAR(3), nullable=False),
        sa.Column("fifa_ranking", sa.Integer(), nullable=True),
        sa.Column("group_letter", sa.CHAR(1), nullable=True),
        sa.Column("avg_goals_scored", sa.Numeric(4, 2), nullable=True),
        sa.Column("avg_goals_conceded", sa.Numeric(4, 2), nullable=True),
        sa.Column("form_points", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.UniqueConstraint("name", name="uq_teams_name"),
    )

    # ------------------------------------------------------------------
    # 2. head_to_head
    # ------------------------------------------------------------------
    op.create_table(
        "head_to_head",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "team_a_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column(
            "team_b_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column("match_date", sa.Date(), nullable=False),
        sa.Column("team_a_score", sa.Integer(), nullable=False),
        sa.Column("team_b_score", sa.Integer(), nullable=False),
        sa.Column("competition", sa.String(100), nullable=True),
        sa.CheckConstraint("team_a_id < team_b_id", name="h2h_team_order"),
    )

    # ------------------------------------------------------------------
    # 3. matches
    # ------------------------------------------------------------------
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(50), unique=True, nullable=True),
        sa.Column(
            "home_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column(
            "away_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("venue", sa.String(150), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'scheduled'"),
        ),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('scheduled','live','halftime','finished','postponed','cancelled')",
            name="chk_status",
        ),
    )
    op.create_index("idx_matches_status", "matches", ["status"])
    op.create_index("idx_matches_scheduled_at", "matches", ["scheduled_at"])
    op.create_index("idx_matches_stage", "matches", ["stage"])

    # ------------------------------------------------------------------
    # 4. live_events
    # ------------------------------------------------------------------
    op.create_table(
        "live_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id"),
            nullable=False,
        ),
        sa.Column("external_event_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=True,
        ),
        sa.Column("player_name", sa.String(100), nullable=True),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("extra_minute", sa.Integer(), nullable=True),
        sa.Column("home_score_after", sa.Integer(), nullable=False),
        sa.Column("away_score_after", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "external_event_id", name="uq_live_events_external_event_id"
        ),
        sa.CheckConstraint(
            "event_type IN ('goal','yellow_card','red_card','substitution','halftime','fulltime')",
            name="chk_event_type",
        ),
    )
    op.create_index("ix_live_events_match_id", "live_events", ["match_id"])

    # ------------------------------------------------------------------
    # 5. model_versions
    # ------------------------------------------------------------------
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("version", sa.String(20), nullable=False, unique=True),
        sa.Column("model_type", sa.String(20), nullable=False),
        sa.Column("training_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.String(300), nullable=False),
        sa.Column("accuracy_on_val", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "model_type IN ('prematch', 'ingame')",
            name="chk_model_type",
        ),
    )
    # Partial unique index: only one active model per type
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_model_versions_active_type "
            "ON model_versions(model_type) WHERE is_active = TRUE"
        )
    )

    # ------------------------------------------------------------------
    # 6. predictions
    # ------------------------------------------------------------------
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            sa.Integer(),
            sa.ForeignKey("model_versions.id"),
            nullable=False,
        ),
        sa.Column("prediction_type", sa.String(10), nullable=False),
        sa.Column("home_win_prob", sa.Numeric(6, 5), nullable=False),
        sa.Column("draw_prob", sa.Numeric(6, 5), nullable=False),
        sa.Column("away_win_prob", sa.Numeric(6, 5), nullable=False),
        sa.Column("expected_home_goals", sa.Numeric(4, 2), nullable=False),
        sa.Column("expected_away_goals", sa.Numeric(4, 2), nullable=False),
        sa.Column("confidence_low", sa.Numeric(6, 5), nullable=False),
        sa.Column("confidence_high", sa.Numeric(6, 5), nullable=False),
        sa.Column("top_factors", postgresql.JSONB(), nullable=False),
        sa.Column(
            "triggering_event_id",
            sa.Integer(),
            sa.ForeignKey("live_events.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "ABS(home_win_prob + draw_prob + away_win_prob - 1.0) < 0.001",
            name="chk_probs_sum",
        ),
        sa.CheckConstraint(
            "prediction_type IN ('prematch', 'live')",
            name="chk_prediction_type",
        ),
    )
    op.create_index(
        "idx_predictions_match_created_at",
        "predictions",
        ["match_id", sa.text("created_at DESC")],
    )

    # ------------------------------------------------------------------
    # 7. accuracy_records
    # ------------------------------------------------------------------
    op.create_table(
        "accuracy_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "prediction_id",
            sa.Integer(),
            sa.ForeignKey("predictions.id"),
            nullable=False,
        ),
        sa.Column("predicted_outcome", sa.String(10), nullable=False),
        sa.Column("actual_outcome", sa.String(10), nullable=False),
        sa.Column("predicted_confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "predicted_outcome IN ('home_win','draw','away_win') AND "
            "actual_outcome IN ('home_win','draw','away_win')",
            name="chk_outcome",
        ),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("accuracy_records")
    op.drop_table("predictions")
    op.drop_index("uq_model_versions_active_type", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index("ix_live_events_match_id", table_name="live_events")
    op.drop_table("live_events")
    op.drop_index("idx_matches_stage", table_name="matches")
    op.drop_index("idx_matches_scheduled_at", table_name="matches")
    op.drop_index("idx_matches_status", table_name="matches")
    op.drop_table("matches")
    op.drop_table("head_to_head")
    op.drop_table("teams")
