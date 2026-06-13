"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("source_chat_id", sa.String(length=64), nullable=True),
        sa.Column("patient_name", sa.String(length=255), nullable=True),
        sa.Column("patient_age", sa.String(length=64), nullable=True),
        sa.Column("patient_weight", sa.String(length=64), nullable=True),
        sa.Column("patient_birth_date", sa.String(length=64), nullable=True),
        sa.Column("companion", sa.String(length=255), nullable=True),
        sa.Column("health_plan", sa.String(length=255), nullable=True),
        sa.Column("origin_unit", sa.String(length=512), nullable=True),
        sa.Column("mp", sa.String(length=255), nullable=True),
        sa.Column("admission_at", sa.String(length=64), nullable=True),
        sa.Column("ecg_at", sa.String(length=64), nullable=True),
        sa.Column("activation_at", sa.String(length=64), nullable=True),
        sa.Column("hma", sa.Text(), nullable=True),
        sa.Column("admission_exam", sa.Text(), nullable=True),
        sa.Column("medications_without_piam", sa.Text(), nullable=True),
        sa.Column("medications_with_piam", sa.Text(), nullable=True),
        sa.Column("ecg_description", sa.Text(), nullable=True),
        sa.Column("current_status", sa.Text(), nullable=True),
        sa.Column("killip", sa.String(length=32), nullable=True),
        sa.Column("hgt", sa.String(length=32), nullable=True),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column("research_notes", sa.Text(), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("piam_formatted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cases_public_id", "cases", ["public_id"], unique=True)
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_source_chat_id", "cases", ["source_chat_id"])

    op.create_table(
        "telegram_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_message_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_messages_message_id", "telegram_messages", ["telegram_message_id"])
    op.create_index("ix_telegram_messages_chat_id", "telegram_messages", ["telegram_chat_id"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("attachment_type", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_type", sa.String(length=32), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)

    op.create_table(
        "ecg_interpretations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("ecg_acquired_at", sa.String(length=64), nullable=True),
        sa.Column("machine_read", sa.Text(), nullable=True),
        sa.Column("ai_read", sa.Text(), nullable=True),
        sa.Column("cardiologist_final_read", sa.Text(), nullable=True),
        sa.Column("stemi_suspected", sa.Boolean(), nullable=True),
        sa.Column("territory", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ecg_interpretations")
    op.drop_index("ix_admin_users_username", table_name="admin_users")
    op.drop_table("admin_users")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("attachments")
    op.drop_index("ix_telegram_messages_chat_id", table_name="telegram_messages")
    op.drop_index("ix_telegram_messages_message_id", table_name="telegram_messages")
    op.drop_table("telegram_messages")
    op.drop_index("ix_cases_source_chat_id", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_public_id", table_name="cases")
    op.drop_table("cases")
