from flask_jwt_extended import current_user

from models.user import User


def owner_required():
    if not isinstance(current_user, User) or current_user.role != "owner":
        return {"msg": "Only owners can access this application"}, 403
    return None
