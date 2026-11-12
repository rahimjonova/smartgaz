"""Boshlang'ich sxema: users, drivers, driver_locations, delivery_routes, orders.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

order_status = sa.Enum(
    "PENDING", "APPROVED", "ON_WAY", "DELIVERED", "CANCELLED", name="order_status"
)
payment_type = sa.Enum("CASH", "ONLINE", name="payment_type")
route_status = sa.Enum("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="route_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("mahalla", sa.String(150), nullable=False),
        sa.Column("street", sa.String(150), nullable=False),
        sa.Column("house_number", sa.String(20), nullable=False),
        sa.Column("lpg_card_id", sa.String(32), nullable=True),
        sa.Column("mahalla_key", sa.Text(), nullable=False),
        sa.Column("household_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"])
    op.create_index("ix_users_mahalla_key", "users", ["mahalla_key"])
    op.create_index("ix_users_household_key", "users", ["household_key"])

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("car_number", sa.String(20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_lat", sa.Float(), nullable=True),
        sa.Column("last_lon", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_drivers"),
        sa.UniqueConstraint("phone_number", name="uq_drivers_phone_number"),
        sa.UniqueConstraint("car_number", name="uq_drivers_car_number"),
        sa.CheckConstraint("capacity > 0", name="ck_drivers_capacity_positive"),
    )

    op.create_table(
        "driver_locations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_locations"),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            name="fk_driver_locations_driver_id_drivers",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_driver_locations_driver_id_recorded_at",
        "driver_locations",
        ["driver_id", "recorded_at"],
    )

    op.create_table(
        "delivery_routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("mahalla_name", sa.String(150), nullable=False),
        sa.Column("mahalla_key", sa.Text(), nullable=False),
        sa.Column("allocated_cylinders", sa.Integer(), nullable=False),
        sa.Column("delivered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", route_status, server_default="PLANNED", nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_delivery_routes"),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            name="fk_delivery_routes_driver_id_drivers",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "driver_id", "date", "mahalla_key", name="uq_delivery_routes_driver_date_mahalla"
        ),
        sa.CheckConstraint("allocated_cylinders > 0", name="ck_delivery_routes_allocated_positive"),
        sa.CheckConstraint(
            "delivered_count >= 0", name="ck_delivery_routes_delivered_non_negative"
        ),
    )
    op.create_index(
        "ix_delivery_routes_date_mahalla_key", "delivery_routes", ["date", "mahalla_key"]
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("status", order_status, server_default="PENDING", nullable=False),
        sa.Column("queue_number", sa.Integer(), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_type", payment_type, server_default="CASH", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_orders_user_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["delivery_routes.id"],
            name="fk_orders_route_id_delivery_routes",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("price >= 0", name="ck_orders_price_non_negative"),
        sa.CheckConstraint("queue_number > 0", name="ck_orders_queue_number_positive"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_route_id", "orders", ["route_id"])
    op.create_index("ix_orders_status_requested_at", "orders", ["status", "requested_at"])
    op.create_index(
        "uq_orders_user_active",
        "orders",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'APPROVED', 'ON_WAY')"),
    )


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("delivery_routes")
    op.drop_table("driver_locations")
    op.drop_table("drivers")
    op.drop_table("users")
    bind = op.get_bind()
    for enum_type in (order_status, payment_type, route_status):
        enum_type.drop(bind, checkfirst=True)
