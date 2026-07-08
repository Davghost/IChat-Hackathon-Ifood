"""add order status and updated_at

Revision ID: 9f2e7c4a1b22
Revises: e41f401bfc61
Create Date: 2026-07-08 00:00:00.000000

"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "9f2e7c4a1b22"
down_revision = "e41f401bfc61"
branch_labels = None
depends_on = None


def upgrade():
    timestamp = datetime.now(timezone.utc)

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=True)
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE orders
            SET status = 'new',
                updated_at = :timestamp
            WHERE status IS NULL
               OR updated_at IS NULL
            """
        ),
        {"timestamp": timestamp},
    )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("status", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False)
        batch_op.create_index(batch_op.f("ix_orders_status"), ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_status"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("status")
