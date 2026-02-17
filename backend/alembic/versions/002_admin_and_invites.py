"""Admin mode and invite-only registration

Revision ID: 002
Revises: 001
Create Date: 2026-02-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add admin and invite tracking to users
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))

    # Create invites table
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_invites_token", "invites", ["token"])
    op.create_index("idx_invites_email", "invites", ["email"])

    # Create settings table (key-value for system config)
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )

    # Seed default settings
    op.execute("INSERT INTO settings (key, value) VALUES ('registration_mode', 'invite_only')")

    # Seed admin user
    op.execute("UPDATE users SET is_admin = true WHERE email = 'mike@mikeayles.com'")


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("invites")
    op.drop_column("users", "invited_by")
    op.drop_column("users", "is_admin")
