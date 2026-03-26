"""Add onboarding, consent, and profile fields to users.

Revision ID: 20260325_0003
Revises: 20260322_0002
Create Date: 2026-03-25 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0003"
down_revision: Union[str, None] = "20260322_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("photo_url", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("blood_group", sa.String(length=8), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("profession", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("health_goals", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "consent_accepted_at")
    op.drop_column("users", "health_goals")
    op.drop_column("users", "profession")
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "blood_group")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "gender")
    op.drop_column("users", "photo_url")
