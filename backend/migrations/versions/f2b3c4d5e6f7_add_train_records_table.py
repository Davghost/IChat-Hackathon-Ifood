"""add train records table

Revision ID: f2b3c4d5e6f7
Revises: 9f2e7c4a1b22
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f2b3c4d5e6f7"
down_revision = "9f2e7c4a1b22"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "train_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_table", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("train_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_train_records_external_id"), ["external_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_train_records_imported_at"), ["imported_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_train_records_payload_hash"), ["payload_hash"], unique=True)
        batch_op.create_index(batch_op.f("ix_train_records_source_table"), ["source_table"], unique=False)


def downgrade():
    with op.batch_alter_table("train_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_train_records_source_table"))
        batch_op.drop_index(batch_op.f("ix_train_records_payload_hash"))
        batch_op.drop_index(batch_op.f("ix_train_records_imported_at"))
        batch_op.drop_index(batch_op.f("ix_train_records_external_id"))

    op.drop_table("train_records")
