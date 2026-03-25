"""Add family profiles, profile-scoped tracking links, and vault table.

Revision ID: 20260322_0002
Revises: 20260311_0001
Create Date: 2026-03-22 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260322_0002"
down_revision: Union[str, None] = "20260311_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("phone_e164", sa.String(length=32), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "phone_e164", name="uq_family_owner_phone"),
    )
    op.create_index("ix_family_members_owner_user_id", "family_members", ["owner_user_id"], unique=False)
    op.create_index("ix_family_members_phone_e164", "family_members", ["phone_e164"], unique=False)

    op.add_column("vital_logs", sa.Column("family_member_id", sa.Integer(), nullable=True))
    op.create_index("ix_vital_logs_family_member_id", "vital_logs", ["family_member_id"], unique=False)
    op.create_foreign_key(
        "fk_vital_logs_family_member_id",
        "vital_logs",
        "family_members",
        ["family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("chronic_symptoms", sa.Column("family_member_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_chronic_symptoms_family_member_id",
        "chronic_symptoms",
        ["family_member_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_chronic_symptoms_family_member_id",
        "chronic_symptoms",
        "family_members",
        ["family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("illness_episodes", sa.Column("family_member_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_illness_episodes_family_member_id",
        "illness_episodes",
        ["family_member_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_illness_episodes_family_member_id",
        "illness_episodes",
        "family_members",
        ["family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("medications", sa.Column("family_member_id", sa.Integer(), nullable=True))
    op.create_index("ix_medications_family_member_id", "medications", ["family_member_id"], unique=False)
    op.create_foreign_key(
        "fk_medications_family_member_id",
        "medications",
        "family_members",
        ["family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("reminders", sa.Column("family_member_id", sa.Integer(), nullable=True))
    op.create_index("ix_reminders_family_member_id", "reminders", ["family_member_id"], unique=False)
    op.create_foreign_key(
        "fk_reminders_family_member_id",
        "reminders",
        "family_members",
        ["family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "health_records",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=500), nullable=True),
        sa.Column("file_url", sa.String(length=1000), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_uploaded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_records_record_type", "health_records", ["record_type"], unique=False)
    op.create_index("ix_health_records_record_date", "health_records", ["record_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_health_records_record_date", table_name="health_records")
    op.drop_index("ix_health_records_record_type", table_name="health_records")
    op.drop_table("health_records")

    op.drop_constraint("fk_reminders_family_member_id", "reminders", type_="foreignkey")
    op.drop_index("ix_reminders_family_member_id", table_name="reminders")
    op.drop_column("reminders", "family_member_id")

    op.drop_constraint("fk_medications_family_member_id", "medications", type_="foreignkey")
    op.drop_index("ix_medications_family_member_id", table_name="medications")
    op.drop_column("medications", "family_member_id")

    op.drop_constraint("fk_illness_episodes_family_member_id", "illness_episodes", type_="foreignkey")
    op.drop_index("ix_illness_episodes_family_member_id", table_name="illness_episodes")
    op.drop_column("illness_episodes", "family_member_id")

    op.drop_constraint("fk_chronic_symptoms_family_member_id", "chronic_symptoms", type_="foreignkey")
    op.drop_index("ix_chronic_symptoms_family_member_id", table_name="chronic_symptoms")
    op.drop_column("chronic_symptoms", "family_member_id")

    op.drop_constraint("fk_vital_logs_family_member_id", "vital_logs", type_="foreignkey")
    op.drop_index("ix_vital_logs_family_member_id", table_name="vital_logs")
    op.drop_column("vital_logs", "family_member_id")

    op.drop_index("ix_family_members_phone_e164", table_name="family_members")
    op.drop_index("ix_family_members_owner_user_id", table_name="family_members")
    op.drop_table("family_members")
