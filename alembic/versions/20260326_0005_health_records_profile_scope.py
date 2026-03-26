"""Add ownership/profile scope fields to health records.

Revision ID: 20260326_0005
Revises: 20260326_0004
Create Date: 2026-03-26 00:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260326_0005"
down_revision: Union[str, None] = "20260326_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "health_records", "created_at"):
        op.add_column(
            "health_records",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column(inspector, "health_records", "updated_at"):
        op.add_column(
            "health_records",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column(inspector, "health_records", "user_id"):
        op.add_column("health_records", sa.Column("user_id", sa.Integer(), nullable=True))

    if not _has_column(inspector, "health_records", "family_member_id"):
        op.add_column("health_records", sa.Column("family_member_id", sa.Integer(), nullable=True))

    # Backfill legacy unscoped rows to first user when possible.
    fallback_user_id = bind.execute(sa.text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).scalar()
    if fallback_user_id is not None:
        bind.execute(
            sa.text("UPDATE health_records SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": int(fallback_user_id)},
        )
    bind.execute(
        sa.text(
            "UPDATE health_records SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE health_records SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
        )
    )

    inspector = sa.inspect(bind)

    if not _has_index(inspector, "health_records", "ix_health_records_user_id"):
        op.create_index("ix_health_records_user_id", "health_records", ["user_id"], unique=False)

    if not _has_index(inspector, "health_records", "ix_health_records_family_member_id"):
        op.create_index(
            "ix_health_records_family_member_id",
            "health_records",
            ["family_member_id"],
            unique=False,
        )

    if not _has_fk(inspector, "health_records", "fk_health_records_user_id"):
        op.create_foreign_key(
            "fk_health_records_user_id",
            "health_records",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if not _has_fk(inspector, "health_records", "fk_health_records_family_member_id"):
        op.create_foreign_key(
            "fk_health_records_family_member_id",
            "health_records",
            "family_members",
            ["family_member_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.alter_column("health_records", "created_at", nullable=False)
    op.alter_column("health_records", "updated_at", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_fk(inspector, "health_records", "fk_health_records_family_member_id"):
        op.drop_constraint("fk_health_records_family_member_id", "health_records", type_="foreignkey")

    if _has_fk(inspector, "health_records", "fk_health_records_user_id"):
        op.drop_constraint("fk_health_records_user_id", "health_records", type_="foreignkey")

    if _has_index(inspector, "health_records", "ix_health_records_family_member_id"):
        op.drop_index("ix_health_records_family_member_id", table_name="health_records")

    if _has_index(inspector, "health_records", "ix_health_records_user_id"):
        op.drop_index("ix_health_records_user_id", table_name="health_records")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "health_records", "family_member_id"):
        op.drop_column("health_records", "family_member_id")

    if _has_column(inspector, "health_records", "user_id"):
        op.drop_column("health_records", "user_id")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "health_records", "updated_at"):
        op.drop_column("health_records", "updated_at")

    if _has_column(inspector, "health_records", "created_at"):
        op.drop_column("health_records", "created_at")
