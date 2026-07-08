from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from models.menu_item import MenuItem
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from utils.response_schema import GenericResponse
from .common import (
    MenuItemMessage,
    MenuItemResponse,
    find_owner_restaurant,
    menu_item_response,
    owner_controller,
    owner_required,
)


@owner_controller.post("/menus")
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_201=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def create_menu_item():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    restaurant = find_owner_restaurant(data.restaurant_id)
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    menu_item = MenuItem(
        title=data.title,
        name=data.name,
        price=float(data.price),
        description=data.description,
        owner_id=current_user.id,
        restaurant_id=restaurant.id,
    )
    db.session.add(menu_item)
    db.session.commit()

    return menu_item_response(menu_item), 201


@owner_controller.get("/menus")
@api.validate(resp=Response(HTTP_200=list[MenuItemResponse], HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def list_menu_items():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    items = MenuItem.query.filter_by(owner_id=current_user.id).all()
    return [menu_item_response(item) for item in items], 200


@owner_controller.put("/menus/<int:menu_id>")
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_200=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def update_menu_item(menu_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    data = request.context.json
    restaurant = find_owner_restaurant(data.restaurant_id)
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    menu_item.title = data.title
    menu_item.name = data.name
    menu_item.price = float(data.price)
    menu_item.description = data.description
    menu_item.restaurant_id = restaurant.id
    db.session.commit()

    return menu_item_response(menu_item), 200


@owner_controller.delete("/menus/<int:menu_id>")
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def delete_menu_item(menu_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    db.session.delete(menu_item)
    db.session.commit()

    return {"msg": "Menu item deleted successfully"}, 200
