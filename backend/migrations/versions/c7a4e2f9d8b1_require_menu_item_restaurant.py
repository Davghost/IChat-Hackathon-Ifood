"""require menu items to belong to restaurants

Revision ID: c7a4e2f9d8b1
Revises: b4a9f8d2c1e3
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c7a4e2f9d8b1"
down_revision = "b4a9f8d2c1e3"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE menu_items
            SET restaurant_id = (
                SELECT restaurants.id
                FROM restaurants
                WHERE restaurants.owner_id = menu_items.owner_id
                ORDER BY restaurants.id
                LIMIT 1
            )
            WHERE restaurant_id IS NULL
              AND EXISTS (
                SELECT 1
                FROM restaurants
                WHERE restaurants.owner_id = menu_items.owner_id
              )
            """
        )
    )

    remaining = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM menu_items
            WHERE restaurant_id IS NULL
            """
        )
    ).scalar_one()
    if remaining:
        raise RuntimeError(
            "Cannot require menu_items.restaurant_id while menu items without "
            "a matching owner restaurant still exist."
        )

    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.alter_column(
            "restaurant_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.alter_column(
            "restaurant_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
