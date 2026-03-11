"""Initial schema with all current tables, links, and constraints.

Revision ID: 20260311_0001
Revises:
Create Date: 2026-03-11 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260311_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("firebase_uid"),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=False)

    op.create_table(
        "home_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("theme_mode", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "theme_mode IN ('light', 'dark', 'system')",
            name="ck_home_preferences_theme_mode_values",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_home_preferences_user_id", "home_preferences", ["user_id"], unique=False)

    op.create_table(
        "vital_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("vital_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("value_secondary", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vital_logs_user_id", "vital_logs", ["user_id"], unique=False)
    op.create_index("ix_vital_logs_vital_type", "vital_logs", ["vital_type"], unique=False)

    op.create_table(
        "chronic_symptoms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symptom_name", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("body_area", sa.String(length=64), nullable=True),
        sa.Column("triggers", sa.Text(), nullable=True),
        sa.Column("first_noticed", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity BETWEEN 1 AND 10", name="ck_chronic_symptoms_severity_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chronic_symptoms_user_id", "chronic_symptoms", ["user_id"], unique=False)

    op.create_table(
        "illness_episodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_illness_episodes_valid_date_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_illness_episodes_user_id", "illness_episodes", ["user_id"], unique=False)

    op.create_table(
        "medications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("dosage", sa.String(length=64), nullable=False),
        sa.Column("frequency", sa.String(length=64), nullable=False),
        sa.Column("route", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("prescribing_doctor", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_medications_valid_date_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medications_user_id", "medications", ["user_id"], unique=False)

    op.create_table(
        "home_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_route", sa.String(length=256), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "is_read = FALSE OR read_at IS NOT NULL",
            name="ck_home_notifications_read_requires_timestamp",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_home_notifications_is_read", "home_notifications", ["is_read"], unique=False)
    op.create_index("ix_home_notifications_user_id", "home_notifications", ["user_id"], unique=False)

    op.create_table(
        "illness_details",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("episode_id", sa.Integer(), nullable=False),
        sa.Column("detail_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["illness_episodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_illness_details_episode_id", "illness_details", ["episode_id"], unique=False)

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("reminder_type", sa.String(length=32), nullable=False),
        sa.Column("linked_medication_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("recurrence", sa.String(length=32), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "recurrence IN ('daily', 'weekly', 'monthly', 'once')",
            name="ck_reminders_recurrence_values",
        ),
        sa.ForeignKeyConstraint(["linked_medication_id"], ["medications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reminders_user_id", table_name="reminders")
    op.drop_table("reminders")

    op.drop_index("ix_illness_details_episode_id", table_name="illness_details")
    op.drop_table("illness_details")

    op.drop_index("ix_home_notifications_user_id", table_name="home_notifications")
    op.drop_index("ix_home_notifications_is_read", table_name="home_notifications")
    op.drop_table("home_notifications")

    op.drop_index("ix_medications_user_id", table_name="medications")
    op.drop_table("medications")

    op.drop_index("ix_illness_episodes_user_id", table_name="illness_episodes")
    op.drop_table("illness_episodes")

    op.drop_index("ix_chronic_symptoms_user_id", table_name="chronic_symptoms")
    op.drop_table("chronic_symptoms")

    op.drop_index("ix_vital_logs_vital_type", table_name="vital_logs")
    op.drop_index("ix_vital_logs_user_id", table_name="vital_logs")
    op.drop_table("vital_logs")

    op.drop_index("ix_home_preferences_user_id", table_name="home_preferences")
    op.drop_table("home_preferences")

    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_table("users")
