from factory import api, db
from flask import Blueprint, request
from models.user import User
from models.menu_item import MenuItem
from models.restaurant import Restaurant
from utils.response_schema import GenericResponse
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError
from flask_jwt_extended import jwt_required, current_user
from pydantic import BaseModel

owner_controller = Blueprint('owner_controller', __name__, url_prefix='/api/owner')


class RestaurantMessage(BaseModel):
    name: str
    description: str


class RestaurantResponse(BaseModel):
    id: int
    name: str
    description: str


class MenuItemMessage(BaseModel):
    title: str
    name: str
    price: float
    description: str
    restaurant_id: int


class MenuItemResponse(BaseModel):
    id: int
    title: str
    name: str
    price: float
    description: str
    restaurant_id: int


def _owner_required():
    if not isinstance(current_user, User) or current_user.role != 'owner':
        return {'msg': 'Only owners can manage restaurants and menus'}, 403

    return None


def _find_owner_restaurant(restaurant_id):
    return Restaurant.query.filter_by(
        id=restaurant_id,
        owner_id=current_user.id,
    ).first()


def _restaurant_response(restaurant):
    return RestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        description=restaurant.description,
    ).model_dump()


def _menu_item_response(menu_item):
    return MenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
        restaurant_id=menu_item.restaurant_id,
    ).model_dump()


@owner_controller.post('/restaurants')
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_201=RestaurantResponse, HTTP_400=GenericResponse),
    tags=['owner'],
)
@jwt_required()
def create_restaurant():
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    data = request.json
    restaurant = Restaurant(
        name=data['name'],
        description=data['description'],
        owner=current_user._get_current_object(),
    )
    db.session.add(restaurant)
    db.session.commit()

    return _restaurant_response(restaurant), 201


@owner_controller.get('/restaurants')
@api.validate(resp=Response(HTTP_200=list[RestaurantResponse]), tags=['owner'])
@jwt_required()
def list_restaurants():
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    restaurants = Restaurant.query.filter_by(owner_id=current_user.id).all()
    return [_restaurant_response(restaurant) for restaurant in restaurants], 200


@owner_controller.put('/restaurants/<int:restaurant_id>')
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse),
    tags=['owner'],
)
@jwt_required()
def update_restaurant(restaurant_id):
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    restaurant = _find_owner_restaurant(restaurant_id)
    if not restaurant:
        return {'msg': 'Restaurant not found'}, 404

    data = request.json
    restaurant.name = data['name']
    restaurant.description = data['description']
    db.session.commit()

    return _restaurant_response(restaurant), 200


@owner_controller.delete('/restaurants/<int:restaurant_id>')
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=['owner'])
@jwt_required()
def delete_restaurant(restaurant_id):
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    restaurant = _find_owner_restaurant(restaurant_id)
    if not restaurant:
        return {'msg': 'Restaurant not found'}, 404

    db.session.delete(restaurant)
    db.session.commit()

    return {'msg': 'Restaurant deleted successfully'}, 200


@owner_controller.post('/menus')
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_201=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=['owner'],
)
@jwt_required()
def create_menu_item():
    data = request.json
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    restaurant = _find_owner_restaurant(data['restaurant_id'])
    if not restaurant:
        return {'msg': 'Restaurant not found'}, 404

    menu_item = MenuItem(
        title=data['title'],
        name=data['name'],
        price=float(data['price']),
        description=data['description'],
        owner_id=current_user.id,
        restaurant_id=restaurant.id,
    )
    db.session.add(menu_item)
    db.session.commit()

    return _menu_item_response(menu_item), 201


@owner_controller.get('/menus')
@api.validate(resp=Response(HTTP_200=list[MenuItemResponse], HTTP_404=GenericResponse), tags=['owner'])
@jwt_required()
def list_menu_items():
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    items = MenuItem.query.filter_by(owner_id=current_user.id).all()
    return [_menu_item_response(item) for item in items], 200


@owner_controller.put('/menus/<int:menu_id>')
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_200=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=['owner'],
)
@jwt_required()
def update_menu_item(menu_id):
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {'msg': 'Menu item not found'}, 404

    data = request.json
    restaurant = _find_owner_restaurant(data['restaurant_id'])
    if not restaurant:
        return {'msg': 'Restaurant not found'}, 404

    menu_item.title = data['title']
    menu_item.name = data['name']
    menu_item.price = float(data['price'])
    menu_item.description = data['description']
    menu_item.restaurant_id = restaurant.id
    db.session.commit()

    return _menu_item_response(menu_item), 200


@owner_controller.delete('/menus/<int:menu_id>')
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=['owner'])
@jwt_required()
def delete_menu_item(menu_id):
    auth_error = _owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {'msg': 'Menu item not found'}, 404

    db.session.delete(menu_item)
    db.session.commit()

    return {'msg': 'Menu item deleted successfully'}, 200
