"""Drop user_source_permissions table — permissions now managed via groups only

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_user_source_permissions_source_id", table_name="user_source_permissions")
    op.drop_index("ix_user_source_permissions_user_id", table_name="user_source_permissions")
    op.drop_table("user_source_permissions")


def downgrade() -> None:
    op.create_table(
        "user_source_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("permitted_tables", postgresql.JSON, nullable=True),
    )
    op.create_index("ix_user_source_permissions_user_id", "user_source_permissions", ["user_id"])
    op.create_index("ix_user_source_permissions_source_id", "user_source_permissions", ["source_id"])
