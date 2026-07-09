from main import app
from factory import db
from models.user import User


USERNAME = "string"
EMAIL = "string"
PASSWORD = "string"
ROLE = "owner"


def create_user():

    existing_user = User.query.filter(
        (User.username == USERNAME) |
        (User.email == EMAIL)
    ).first()


    if existing_user:
        print("User already exists:")
        print(existing_user)
        return


    user = User(
        username=USERNAME,
        email=EMAIL,
        role=ROLE
    )

    # gera o password_hash automaticamente
    user.password = PASSWORD


    db.session.add(user)
    db.session.commit()


    print("User created successfully!")
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role}")



if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        create_user()