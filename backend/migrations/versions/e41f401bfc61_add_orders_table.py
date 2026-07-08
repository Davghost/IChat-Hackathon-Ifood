"""add orders table

Revision ID: e41f401bfc61
Revises: c7a4e2f9d8b1
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e41f401bfc61"
down_revision = "c7a4e2f9d8b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_orders_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_orders_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_orders_menu_item_id"), ["menu_item_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_orders_owner_id"), ["owner_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_orders_restaurant_id"), ["restaurant_id"], unique=False)


def downgrade():
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_restaurant_id"))
        batch_op.drop_index(batch_op.f("ix_orders_owner_id"))
        batch_op.drop_index(batch_op.f("ix_orders_menu_item_id"))
        batch_op.drop_index(batch_op.f("ix_orders_customer_id"))
        batch_op.drop_index(batch_op.f("ix_orders_created_at"))

    op.drop_table("orders")
