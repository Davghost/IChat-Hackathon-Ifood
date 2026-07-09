from flask_jwt_extended import current_user

from models.restaurant import Restaurant
from models.user import User


def owner_required():
    if not isinstance(current_user, User) or current_user.role != "owner":
        return {"msg": "Only owners can manage restaurants and menus"}, 403
    return None


def get_owner_restaurant():
    return Restaurant.query.filter_by(owner_id=current_user.id).first()
