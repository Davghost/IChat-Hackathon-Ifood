from datetime import datetime

from factory import api
from flask import Blueprint, request
from models.user import UserResponse
from models.restaurant import Restaurant
from utils.response_schema import GenericResponse
from spectree import Response
from flask_jwt_extended import jwt_required, current_user
from pydantic import BaseModel
from sqlalchemy.orm import selectinload

user_controller = Blueprint("user_controller", __name__, url_prefix="/api/users")

DEFAULT_RESTAURANTS_PER_PAGE = 20
MAX_RESTAURANTS_PER_PAGE = 50


class PublicMenuItemResponse(BaseModel):
    id: int
    title: str
    name: str
    price: float
    description: str
    owner_id: int
    restaurant_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class PublicRestaurantResponse(BaseModel):
    id: int
    name: str
    description: str
    menu_items: list[PublicMenuItemResponse]


class RestaurantsPageResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
    restaurants: list[PublicRestaurantResponse]


def _positive_int_arg(name, default):
    raw_value = request.args.get(name, default)

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, ({'msg': f'{name} must be a positive integer'}, 400)

    if value < 1:
        return None, ({'msg': f'{name} must be a positive integer'}, 400)

    return value, None


def _menu_item_response(menu_item):
    return PublicMenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
        owner_id=menu_item.owner_id,
        restaurant_id=menu_item.restaurant_id,
        created_at=menu_item.created_at,
        updated_at=menu_item.updated_at,
    )


def _restaurant_response(restaurant):
    return PublicRestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        description=restaurant.description,
        menu_items=[
            _menu_item_response(menu_item)
            for menu_item in sorted(restaurant.menu_items, key=lambda item: item.id)
        ],
    )


@user_controller.get("/me")
@api.validate(
    resp=Response(HTTP_200=UserResponse, HTTP_404=GenericResponse), tags=["users"]
)
@jwt_required()
def get_user():
    """
    Get logged user
    """

    response = UserResponse.model_validate(current_user).to_response_dict()

    return response, 200


@user_controller.get("/restaurants")
@api.validate(
    resp=Response(HTTP_200=RestaurantsPageResponse, HTTP_400=GenericResponse),
    tags=["users"],
)
@jwt_required()
def list_restaurants_with_menus():
    page, error = _positive_int_arg("page", 1)
    if error:
        return error

    per_page, error = _positive_int_arg("per_page", DEFAULT_RESTAURANTS_PER_PAGE)
    if error:
        return error

    per_page = min(per_page, MAX_RESTAURANTS_PER_PAGE)

    pagination = Restaurant.query.options(
        selectinload(Restaurant.menu_items)
    ).order_by(Restaurant.id).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    response = RestaurantsPageResponse(
        page=pagination.page,
        per_page=pagination.per_page,
        total=pagination.total,
        pages=pagination.pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
        restaurants=[
            _restaurant_response(restaurant)
            for restaurant in pagination.items
        ],
    )

    return response.model_dump(mode="json"), 200
