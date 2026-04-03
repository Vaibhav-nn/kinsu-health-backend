"""Add dashboard support entities for appointments, exercise, vault filters, and adherence.

Revision ID: 20260403_0006
Revises: 20260326_0005
Create Date: 2026-04-03 11:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260403_0006"
down_revision: Union[str, None] = "20260326_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "family_members"):
        if not _has_column(inspector, "family_members", "blood_group"):
            op.add_column("family_members", sa.Column("blood_group", sa.String(length=8), nullable=True))
        if not _has_column(inspector, "family_members", "health_conditions"):
            op.add_column("family_members", sa.Column("health_conditions", sa.JSON(), nullable=True))

    if _has_table(inspector, "health_records"):
        if not _has_column(inspector, "health_records", "document_subtype"):
            op.add_column("health_records", sa.Column("document_subtype", sa.String(length=100), nullable=True))
        if not _has_column(inspector, "health_records", "provider_name"):
            op.add_column("health_records", sa.Column("provider_name", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "health_records", "tags"):
            op.add_column("health_records", sa.Column("tags", sa.JSON(), nullable=True))

        inspector = sa.inspect(bind)
        if not _has_index(inspector, "health_records", "ix_health_records_document_subtype"):
            op.create_index("ix_health_records_document_subtype", "health_records", ["document_subtype"], unique=False)
        if not _has_index(inspector, "health_records", "ix_health_records_provider_name"):
            op.create_index("ix_health_records_provider_name", "health_records", ["provider_name"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "appointments"):
        op.create_table(
            "appointments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("doctor_name", sa.String(length=255), nullable=False),
            sa.Column("specialty", sa.String(length=128), nullable=True),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_appointments_user_id", "appointments", ["user_id"], unique=False)
        op.create_index("ix_appointments_family_member_id", "appointments", ["family_member_id"], unique=False)
        op.create_index("ix_appointments_appointment_at", "appointments", ["appointment_at"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "medication_dose_logs"):
        op.create_table(
            "medication_dose_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("medication_id", sa.Integer(), sa.ForeignKey("medications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scheduled_for", sa.Date(), nullable=False),
            sa.Column("scheduled_time", sa.Time(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_medication_dose_logs_user_id", "medication_dose_logs", ["user_id"], unique=False)
        op.create_index("ix_medication_dose_logs_family_member_id", "medication_dose_logs", ["family_member_id"], unique=False)
        op.create_index("ix_medication_dose_logs_medication_id", "medication_dose_logs", ["medication_id"], unique=False)
        op.create_index("ix_medication_dose_logs_scheduled_for", "medication_dose_logs", ["scheduled_for"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "symptom_events"):
        op.create_table(
            "symptom_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("symptom_name", sa.String(length=128), nullable=False),
            sa.Column("severity", sa.Integer(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_symptom_events_user_id", "symptom_events", ["user_id"], unique=False)
        op.create_index("ix_symptom_events_family_member_id", "symptom_events", ["family_member_id"], unique=False)
        op.create_index("ix_symptom_events_symptom_name", "symptom_events", ["symptom_name"], unique=False)
        op.create_index("ix_symptom_events_occurred_at", "symptom_events", ["occurred_at"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "activity_logs"):
        op.create_table(
            "activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("activity_name", sa.String(length=128), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False),
            sa.Column("calories_burned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("distance_km", sa.Float(), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"], unique=False)
        op.create_index("ix_activity_logs_family_member_id", "activity_logs", ["family_member_id"], unique=False)
        op.create_index("ix_activity_logs_category", "activity_logs", ["category"], unique=False)
        op.create_index("ix_activity_logs_activity_name", "activity_logs", ["activity_name"], unique=False)
        op.create_index("ix_activity_logs_logged_at", "activity_logs", ["logged_at"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "connected_services"):
        op.create_table(
            "connected_services",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider_name", sa.String(length=255), nullable=False),
            sa.Column("provider_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="link"),
            sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_connected_services_user_id", "connected_services", ["user_id"], unique=False)
        op.create_index("ix_connected_services_provider_name", "connected_services", ["provider_name"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "lab_parameter_results"):
        op.create_table(
            "lab_parameter_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("record_id", sa.String(), sa.ForeignKey("health_records.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("parameter_key", sa.String(length=64), nullable=False),
            sa.Column("parameter_label", sa.String(length=128), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column("observed_on", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("reference_low", sa.Float(), nullable=True),
            sa.Column("reference_high", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_lab_parameter_results_record_id", "lab_parameter_results", ["record_id"], unique=False)
        op.create_index("ix_lab_parameter_results_user_id", "lab_parameter_results", ["user_id"], unique=False)
        op.create_index("ix_lab_parameter_results_family_member_id", "lab_parameter_results", ["family_member_id"], unique=False)
        op.create_index("ix_lab_parameter_results_parameter_key", "lab_parameter_results", ["parameter_key"], unique=False)
        op.create_index("ix_lab_parameter_results_observed_on", "lab_parameter_results", ["observed_on"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "caregiver_permissions"):
        op.create_table(
            "caregiver_permissions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_key", sa.String(length=64), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("family_member_id", "permission_key", name="uq_caregiver_permission_key"),
        )
        op.create_index("ix_caregiver_permissions_owner_user_id", "caregiver_permissions", ["owner_user_id"], unique=False)
        op.create_index("ix_caregiver_permissions_family_member_id", "caregiver_permissions", ["family_member_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in [
        ("caregiver_permissions", ["ix_caregiver_permissions_family_member_id", "ix_caregiver_permissions_owner_user_id"]),
        ("lab_parameter_results", ["ix_lab_parameter_results_observed_on", "ix_lab_parameter_results_parameter_key", "ix_lab_parameter_results_family_member_id", "ix_lab_parameter_results_user_id", "ix_lab_parameter_results_record_id"]),
        ("connected_services", ["ix_connected_services_provider_name", "ix_connected_services_user_id"]),
        ("activity_logs", ["ix_activity_logs_logged_at", "ix_activity_logs_activity_name", "ix_activity_logs_category", "ix_activity_logs_family_member_id", "ix_activity_logs_user_id"]),
        ("symptom_events", ["ix_symptom_events_occurred_at", "ix_symptom_events_symptom_name", "ix_symptom_events_family_member_id", "ix_symptom_events_user_id"]),
        ("medication_dose_logs", ["ix_medication_dose_logs_scheduled_for", "ix_medication_dose_logs_medication_id", "ix_medication_dose_logs_family_member_id", "ix_medication_dose_logs_user_id"]),
        ("appointments", ["ix_appointments_appointment_at", "ix_appointments_family_member_id", "ix_appointments_user_id"]),
    ]:
        inspector = sa.inspect(bind)
        if _has_table(inspector, table_name):
            for index_name in indexes:
                if _has_index(inspector, table_name, index_name):
                    op.drop_index(index_name, table_name=table_name)
                    inspector = sa.inspect(bind)
            op.drop_table(table_name)

    inspector = sa.inspect(bind)
    if _has_table(inspector, "health_records"):
        if _has_index(inspector, "health_records", "ix_health_records_provider_name"):
            op.drop_index("ix_health_records_provider_name", table_name="health_records")
        if _has_index(inspector, "health_records", "ix_health_records_document_subtype"):
            op.drop_index("ix_health_records_document_subtype", table_name="health_records")
        inspector = sa.inspect(bind)
        for column_name in ["tags", "provider_name", "document_subtype"]:
            if _has_column(inspector, "health_records", column_name):
                op.drop_column("health_records", column_name)
                inspector = sa.inspect(bind)

    inspector = sa.inspect(bind)
    if _has_table(inspector, "family_members"):
        for column_name in ["health_conditions", "blood_group"]:
            if _has_column(inspector, "family_members", column_name):
                op.drop_column("family_members", column_name)
                inspector = sa.inspect(bind)
