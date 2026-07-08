from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from models.restaurant import Restaurant
from spectree import Response

from utils.response_schema import GenericResponse
from .common import (
    RestaurantMessage,
    RestaurantResponse,
    get_owner_restaurant,
    owner_controller,
    owner_required,
    restaurant_response,
)


@owner_controller.post("/restaurant")
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

    if get_owner_restaurant():
        return {"msg": "Owner already has a restaurant"}, 400

    data = request.context.json
    restaurant = Restaurant(
        name=data.name,
        description=data.description,
        owner=current_user._get_current_object(),
    )
    db.session.add(restaurant)
    db.session.commit()

    return restaurant_response(restaurant), 201


@owner_controller.get("/restaurant")
@api.validate(resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def get_restaurant():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    return restaurant_response(restaurant), 200


@owner_controller.put("/restaurant")
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse),
    tags=["owner"],
)
@jwt_required()
def update_restaurant():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    data = request.context.json
    restaurant.name = data.name
    restaurant.description = data.description
    db.session.commit()

    return restaurant_response(restaurant), 200


@owner_controller.delete("/restaurant")
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def delete_restaurant():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    db.session.delete(restaurant)
    db.session.commit()

    return {"msg": "Restaurant deleted successfully"}, 200
