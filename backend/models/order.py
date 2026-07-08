from datetime import datetime, timezone

from factory import db

ORDER_STATUS_NEW = "new"
ORDER_STATUS_PREPARING = "preparing"
ORDER_STATUS_READY = "ready"
ORDER_STATUS_DELIVERED = "delivered"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUSES = (
    ORDER_STATUS_NEW,
    ORDER_STATUS_PREPARING,
    ORDER_STATUS_READY,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELLED,
)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    restaurant_id = db.Column(
        db.Integer,
        db.ForeignKey("restaurants.id"),
        nullable=False,
        index=True,
    )
    menu_item_id = db.Column(
        db.Integer,
        db.ForeignKey("menu_items.id"),
        nullable=False,
        index=True,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(32), nullable=False, default=ORDER_STATUS_NEW, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    customer = db.relationship("User", foreign_keys=[customer_id])
    owner = db.relationship("User", foreign_keys=[owner_id])
    restaurant = db.relationship("Restaurant")
    menu_item = db.relationship("MenuItem")

    def __repr__(self) -> str:
        return f"<Order {self.id}>"
