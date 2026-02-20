"""Add OAuth columns to users table

Revision ID: 003
Revises: 002
Create Date: 2026-02-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("oauth_sub", sa.String(255), nullable=True))
    op.create_unique_constraint(
        "uq_users_oauth_provider_sub", "users", ["oauth_provider", "oauth_sub"]
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(255), nullable=False
    )
    op.drop_constraint("uq_users_oauth_provider_sub", "users", type_="unique")
    op.drop_column("users", "oauth_sub")
    op.drop_column("users", "oauth_provider")
