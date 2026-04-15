"""Add groups, group_memberships, group_source_permissions tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "group_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"])
    op.create_index("ix_group_memberships_user_id", "group_memberships", ["user_id"])

    op.create_table(
        "group_source_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permitted_tables", postgresql.JSON, nullable=True),
        sa.UniqueConstraint("group_id", "source_id", name="uq_group_source"),
    )
    op.create_index("ix_group_source_permissions_group_id", "group_source_permissions", ["group_id"])
    op.create_index("ix_group_source_permissions_source_id", "group_source_permissions", ["source_id"])


def downgrade() -> None:
    op.drop_table("group_source_permissions")
    op.drop_table("group_memberships")
    op.drop_table("groups")
