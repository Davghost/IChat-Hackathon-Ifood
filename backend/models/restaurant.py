from datetime import datetime, timezone

from sqlalchemy.orm import validates

from factory import db


class Restaurant(db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = db.relationship("User", back_populates="restaurants")
    menu_items = db.relationship(
        "MenuItem",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy=True,
    )

    @validates("owner_id")
    def validate_owner_id(self, key, owner_id):
        if owner_id is None:
            return owner_id

        from models.user import User

        owner = db.session.get(User, owner_id)
        if owner is None or owner.role != "owner":
            raise ValueError(
                "Restaurant owner_id must reference a user with role='owner'"
            )

        return owner_id

    @validates("owner")
    def validate_owner(self, key, owner):
        if owner is not None and owner.role != "owner":
            raise ValueError("Restaurant owner must be a user with role='owner'")
        return owner

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
