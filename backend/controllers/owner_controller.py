from factory import api, db
from flask import Blueprint, request
from models.user import User
from models.menu_item import MenuItem
from utils.response_schema import GenericResponse
from spectree import Response
from flask_jwt_extended import jwt_required, current_user
from pydantic import BaseModel

owner_controller = Blueprint('owner_controller', __name__, url_prefix='/api/owner')


class MenuItemMessage(BaseModel):
    title: str
    name: str
    price: float
    description: str


class MenuItemResponse(BaseModel):
    id: int
    title: str
    name: str
    price: float
    description: str


@owner_controller.post('/menus')
@api.validate(
    json=MenuItemMessage,
    resp=Response(HTTP_201=MenuItemResponse, HTTP_400=GenericResponse),
    tags=['owner'],
)
@jwt_required()
def create_menu_item():
    data = request.json
    if not isinstance(current_user, User) or current_user.role != 'owner':
        return {'msg': 'Only owners can manage menus'}, 403

    menu_item = MenuItem(
        title=data['title'],
        name=data['name'],
        price=float(data['price']),
        description=data['description'],
        owner_id=current_user.id,
    )
    db.session.add(menu_item)
    db.session.commit()

    return MenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
    ).model_dump(), 201


@owner_controller.get('/menus')
@api.validate(resp=Response(HTTP_200=list[MenuItemResponse], HTTP_404=GenericResponse), tags=['owner'])
@jwt_required()
def list_menu_items():
    if not isinstance(current_user, User) or current_user.role != 'owner':
        return {'msg': 'Only owners can manage menus'}, 403

    items = MenuItem.query.filter_by(owner_id=current_user.id).all()
    return [
        MenuItemResponse(
            id=item.id,
            title=item.title,
            name=item.name,
            price=item.price,
            description=item.description,
        ).model_dump()
        for item in items
    ], 200


@owner_controller.put('/menus/<int:menu_id>')
@api.validate(
    json=MenuItemMessage,
    resp=Response(HTTP_200=MenuItemResponse, HTTP_404=GenericResponse),
    tags=['owner'],
)
@jwt_required()
def update_menu_item(menu_id):
    if not isinstance(current_user, User) or current_user.role != 'owner':
        return {'msg': 'Only owners can manage menus'}, 403

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {'msg': 'Menu item not found'}, 404

    data = request.json
    menu_item.title = data['title']
    menu_item.name = data['name']
    menu_item.price = float(data['price'])
    menu_item.description = data['description']
    db.session.commit()

    return MenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
    ).model_dump(), 200


@owner_controller.delete('/menus/<int:menu_id>')
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=['owner'])
@jwt_required()
def delete_menu_item(menu_id):
    if not isinstance(current_user, User) or current_user.role != 'owner':
        return {'msg': 'Only owners can manage menus'}, 403

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {'msg': 'Menu item not found'}, 404

    db.session.delete(menu_item)
    db.session.commit()

    return {'msg': 'Menu item deleted successfully'}, 200
