"""add restaurants

Revision ID: b4a9f8d2c1e3
Revises: 667daf1f929d
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b4a9f8d2c1e3"
down_revision = "667daf1f929d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_restaurants_owner_id"), ["owner_id"], unique=False)

    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("restaurant_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_menu_items_restaurant_id"),
            ["restaurant_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_menu_items_restaurant_id_restaurants",
            "restaurants",
            ["restaurant_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_menu_items_restaurant_id_restaurants",
            type_="foreignkey",
        )
        batch_op.drop_index(batch_op.f("ix_menu_items_restaurant_id"))
        batch_op.drop_column("restaurant_id")

    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_restaurants_owner_id"))

    op.drop_table("restaurants")
