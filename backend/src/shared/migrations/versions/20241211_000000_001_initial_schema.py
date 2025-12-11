# pylint: skip-file
# ruff: noqa
"""Initial schema - create all tables

Revision ID: 001
Revises:
Create Date: 2024-12-11 00:00:00

This migration creates all database tables for the Dora application.
Verified against all SQLAlchemy models on 2024-12-11.

Tables created:
- users: User accounts
- shared_content: Universal content metadata (22 columns)
- user_content_saves: User's saved content items
- clusters: AI-generated content clusters
- cluster_memberships: Junction table for clusters
- processing_jobs: Background job tracking

Enums created:
- sourceplatform: instagram, youtube, unknown
- itemstatus: PENDING, PROCESSING, READY, FAILED
- contentcategory: Travel, Food, Learning, Career, Fitness, Entertainment, Shopping, Tech, Lifestyle, Misc
- intenttype: learn, visit, buy, try, watch, misc
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum types
source_platform_enum = postgresql.ENUM(
    "instagram",
    "youtube",
    "unknown",
    name="sourceplatform",
    create_type=False,
)

item_status_enum = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "READY",
    "FAILED",
    name="itemstatus",
    create_type=False,
)

content_category_enum = postgresql.ENUM(
    "Travel",
    "Food",
    "Learning",
    "Career",
    "Fitness",
    "Entertainment",
    "Shopping",
    "Tech",
    "Lifestyle",
    "Misc",
    name="contentcategory",
    create_type=False,
)

intent_type_enum = postgresql.ENUM(
    "learn",
    "visit",
    "buy",
    "try",
    "watch",
    "misc",
    name="intenttype",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade database schema."""
    # Create enum types
    op.execute("CREATE TYPE sourceplatform AS ENUM ('instagram', 'youtube', 'unknown')")
    op.execute("CREATE TYPE itemstatus AS ENUM ('PENDING', 'PROCESSING', 'READY', 'FAILED')")
    op.execute(
        "CREATE TYPE contentcategory AS ENUM "
        "('Travel', 'Food', 'Learning', 'Career', 'Fitness', "
        "'Entertainment', 'Shopping', 'Tech', 'Lifestyle', 'Misc')"
    )
    op.execute("CREATE TYPE intenttype AS ENUM ('learn', 'visit', 'buy', 'try', 'watch', 'misc')")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Create shared_content table
    op.create_table(
        "shared_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_platform", source_platform_enum, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.Text(), nullable=False, unique=True, index=True),
        sa.Column("status", item_status_enum, nullable=False, default="PENDING", index=True),
        sa.Column("content_category", content_category_enum, nullable=True, index=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("topic_main", sa.Text(), nullable=True),
        sa.Column("subcategories", postgresql.JSONB(), nullable=True),
        sa.Column("locations", postgresql.JSONB(), nullable=True),
        sa.Column("entities", postgresql.JSONB(), nullable=True),
        sa.Column("intent", intent_type_enum, nullable=True),
        sa.Column("visual_description", sa.Text(), nullable=True),
        sa.Column("visual_tags", postgresql.JSONB(), nullable=True),
        sa.Column("embedding_id", sa.Text(), nullable=True),
        sa.Column("save_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Create user_content_saves table
    op.create_table(
        "user_content_saves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "shared_content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shared_content.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("raw_share_text", sa.Text(), nullable=True),
        sa.Column("is_favorited", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # Unique constraint: user can only save same content once
    op.create_unique_constraint(
        "uq_user_content_saves_user_content", "user_content_saves", ["user_id", "shared_content_id"]
    )

    # Create clusters table
    op.create_table(
        "clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("content_category", content_category_enum, nullable=False, index=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Create cluster_memberships table (junction table)
    op.create_table(
        "cluster_memberships",
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clusters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_save_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_content_saves.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # Create processing_jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "shared_content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shared_content.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table("processing_jobs")
    op.drop_table("cluster_memberships")
    op.drop_table("clusters")
    op.drop_table("user_content_saves")
    op.drop_table("shared_content")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS intenttype")
    op.execute("DROP TYPE IF EXISTS contentcategory")
    op.execute("DROP TYPE IF EXISTS itemstatus")
    op.execute("DROP TYPE IF EXISTS sourceplatform")
