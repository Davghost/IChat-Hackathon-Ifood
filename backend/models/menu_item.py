from datetime import datetime, timezone

from factory import db


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    owner = db.relationship("User")

    def __repr__(self) -> str:
        return f"<MenuItem {self.id} {self.name}>"
