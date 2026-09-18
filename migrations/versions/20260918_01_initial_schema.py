"""Initial synthetic security operations schema.

Revision ID: 20260918_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(16), primary_key=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("department", sa.String(40), nullable=False),
        sa.Column("home_country", sa.String(2), nullable=False),
        sa.Column("privileged", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(16), primary_key=True),
        sa.Column("owner_user_id", sa.String(16), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("managed", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(16), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_incident_severity"
        ),
    )
    op.create_table(
        "security_events",
        sa.Column("event_id", sa.String(16), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(16), sa.ForeignKey("users.user_id")),
        sa.Column("source_ip", sa.String(45), nullable=False),
        sa.Column("destination_ip", sa.String(45)),
        sa.Column("device_id", sa.String(16), sa.ForeignKey("devices.device_id")),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("country", sa.String(2)),
        sa.Column("authentication_method", sa.String(24)),
        sa.Column("failed_attempts", sa.Integer()),
        sa.Column("successful_attempts", sa.Integer()),
        sa.Column("privileged_account", sa.Boolean()),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.String(16), sa.ForeignKey("incidents.incident_id")),
        sa.CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_event_severity"
        ),
        sa.CheckConstraint(
            "failed_attempts IS NULL OR failed_attempts >= 0", name="ck_failed_nonnegative"
        ),
        sa.CheckConstraint(
            "successful_attempts IS NULL OR successful_attempts >= 0", name="ck_success_nonnegative"
        ),
    )
    op.create_index("ix_events_user_timestamp", "security_events", ["user_id", "timestamp"])
    op.create_index("ix_events_timestamp", "security_events", ["timestamp"])
    op.create_index("ix_events_type", "security_events", ["event_type"])
    op.create_index("ix_events_severity", "security_events", ["severity"])
    op.create_index("ix_events_source_ip", "security_events", ["source_ip"])
    op.create_index("ix_events_device", "security_events", ["device_id"])
    op.create_index("ix_events_incident", "security_events", ["incident_id"])
    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("actor_user_id", sa.String(16), sa.ForeignKey("users.user_id")),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(40)),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("details", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_events_incident", table_name="security_events")
    op.drop_index("ix_events_device", table_name="security_events")
    op.drop_index("ix_events_source_ip", table_name="security_events")
    op.drop_index("ix_events_severity", table_name="security_events")
    op.drop_index("ix_events_type", table_name="security_events")
    op.drop_index("ix_events_timestamp", table_name="security_events")
    op.drop_index("ix_events_user_timestamp", table_name="security_events")
    op.drop_table("security_events")
    op.drop_table("incidents")
    op.drop_table("devices")
    op.drop_table("users")
