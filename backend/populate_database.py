import os

from factory import db
from main import app
from models.user import User
from sqlalchemy import select


DEFAULT_ADMIN_EMAIL = "admin@hackathon.local"
DEFAULT_ADMIN_PASSWORD = "admin123"

'''
def populate_admin_user():
    admin_email = os.getenv("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
    admin_password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    existing_user = db.session.scalars(
        select(User).filter_by(email=admin_email)
    ).first()

    if existing_user is None:
        existing_user = User(
            username="admin",
            email=admin_email,
            role="admin"
        )
        db.session.add(existing_user)

    existing_user.password = admin_password
    db.session.commit()

    print(f"Admin user ready: {admin_email}")
''' 


def populate_owner():
    user= User(
        username="marcos",
        email="marcos4@gmail.com"
    )

    user.password = "123"

    db.session.add(user)
    db.session.commit()

    print(f"{user.role} created")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        #populate_admin_user()
        populate_owner()
