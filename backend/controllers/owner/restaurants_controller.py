from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from models.restaurant import Restaurant
from spectree import Response

from utils.response_schema import GenericResponse
from .common import (
    RestaurantMessage,
    RestaurantResponse,
    find_owner_restaurant,
    owner_controller,
    owner_required,
    restaurant_response,
)


@owner_controller.post("/restaurants")
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_201=RestaurantResponse, HTTP_400=GenericResponse),
    tags=["owner"],
)
@jwt_required()
def create_restaurant():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    restaurant = Restaurant(
        name=data.name,
        description=data.description,
        owner=current_user._get_current_object(),
    )
    db.session.add(restaurant)
    db.session.commit()

    return restaurant_response(restaurant), 201


@owner_controller.get("/restaurants")
@api.validate(resp=Response(HTTP_200=list[RestaurantResponse]), tags=["owner"])
@jwt_required()
def list_restaurants():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurants = Restaurant.query.filter_by(owner_id=current_user.id).all()
    return [restaurant_response(restaurant) for restaurant in restaurants], 200


@owner_controller.put("/restaurants/<int:restaurant_id>")
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse),
    tags=["owner"],
)
@jwt_required()
def update_restaurant(restaurant_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = find_owner_restaurant(restaurant_id)
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    data = request.context.json
    restaurant.name = data.name
    restaurant.description = data.description
    db.session.commit()

    return restaurant_response(restaurant), 200


@owner_controller.delete("/restaurants/<int:restaurant_id>")
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def delete_restaurant(restaurant_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = find_owner_restaurant(restaurant_id)
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    db.session.delete(restaurant)
    db.session.commit()

    return {"msg": "Restaurant deleted successfully"}, 200
