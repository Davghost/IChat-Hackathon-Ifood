from datetime import datetime

from factory import api, db
from flask import Blueprint, request, url_for
from models.user import UserResponse
from models.menu_item import MenuItem
from models.order import Order
from models.restaurant import Restaurant
from utils.response_schema import GenericResponse
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError
from flask_jwt_extended import jwt_required, current_user
from pydantic import BaseModel, Field
from sqlalchemy.orm import selectinload

user_controller = Blueprint("user_controller", __name__, url_prefix="/api/users")

DEFAULT_RESTAURANTS_PER_PAGE = 20
MAX_RESTAURANTS_PER_PAGE = 50


class RestaurantsQuery(BaseModel):
    page: int = Field(
        default=1,
        ge=1,
        description="Page number to return.",
    )
    per_page: int = Field(
        default=DEFAULT_RESTAURANTS_PER_PAGE,
        ge=1,
        le=MAX_RESTAURANTS_PER_PAGE,
        description="Number of restaurants per page.",
    )


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
    owner_id: int
    created_at: datetime | None
    updated_at: datetime | None
    menu_items: list[PublicMenuItemResponse]


class CreateOrderMessage(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)


class OrderRestaurantResponse(BaseModel):
    id: int
    name: str


class OrderMenuItemResponse(BaseModel):
    id: int
    title: str
    name: str
    price: float


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    quantity: int
    unit_price: float
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime
    restaurant: OrderRestaurantResponse
    menu_item: OrderMenuItemResponse


class PaginationLinks(BaseModel):
    current: str
    first: str | None
    previous: str | None
    next: str | None
    last: str | None


class RestaurantsPageResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
    next_page: int | None
    prev_page: int | None
    first_page: int | None
    last_page: int | None
    links: PaginationLinks
    restaurants: list[PublicRestaurantResponse]


def _page_url(page, per_page):
    args = request.args.to_dict(flat=True)
    args["page"] = page
    args["per_page"] = per_page

    return url_for("user_controller.list_restaurants_with_menus", **args)


def _pagination_links(pagination):
    first_page = 1 if pagination.pages else None
    last_page = pagination.pages or None

    return PaginationLinks(
        current=_page_url(pagination.page, pagination.per_page),
        first=_page_url(first_page, pagination.per_page) if first_page else None,
        previous=(
            _page_url(pagination.prev_num, pagination.per_page)
            if pagination.has_prev
            else None
        ),
        next=(
            _page_url(pagination.next_num, pagination.per_page)
            if pagination.has_next
            else None
        ),
        last=_page_url(last_page, pagination.per_page) if last_page else None,
    )


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
    menu_items = sorted(
        (
            menu_item
            for menu_item in restaurant.menu_items
            if menu_item.restaurant_id == restaurant.id
        ),
        key=lambda item: item.id,
    )

    return PublicRestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        description=restaurant.description,
        owner_id=restaurant.owner_id,
        created_at=restaurant.created_at,
        updated_at=restaurant.updated_at,
        menu_items=[
            _menu_item_response(menu_item)
            for menu_item in menu_items
        ],
    )


def _order_response(order):
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        restaurant=OrderRestaurantResponse(
            id=order.restaurant.id,
            name=order.restaurant.name,
        ),
        menu_item=OrderMenuItemResponse(
            id=order.menu_item.id,
            title=order.menu_item.title,
            name=order.menu_item.name,
            price=order.unit_price,
        ),
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


@user_controller.post("/orders")
@api.validate(
    json=CreateOrderMessage,
    resp=Response(
        HTTP_201=OrderResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["users"],
)
@jwt_required()
def create_order():
    data = request.json
    menu_item = MenuItem.query.options(
        selectinload(MenuItem.restaurant)
    ).filter_by(id=data["menu_item_id"]).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    quantity = int(data["quantity"])
    total_price = round(menu_item.price * quantity, 2)

    order = Order(
        customer_id=current_user.id,
        owner_id=menu_item.owner_id,
        restaurant_id=menu_item.restaurant_id,
        menu_item_id=menu_item.id,
        quantity=quantity,
        unit_price=menu_item.price,
        total_price=total_price,
    )
    db.session.add(order)
    db.session.commit()

    order = Order.query.options(
        selectinload(Order.restaurant),
        selectinload(Order.menu_item),
    ).filter_by(id=order.id).first()

    return _order_response(order).model_dump(mode="json"), 201


@user_controller.get("/restaurants")
@api.validate(
    query=RestaurantsQuery,
    resp=Response(
        HTTP_200=RestaurantsPageResponse,
        HTTP_400=SpectreeValidationError,
    ),
    tags=["users"],
)
@jwt_required()
def list_restaurants_with_menus():
    query = request.context.query

    pagination = Restaurant.query.options(
        selectinload(Restaurant.menu_items)
    ).order_by(Restaurant.id).paginate(
        page=query.page,
        per_page=query.per_page,
        error_out=False,
    )

    response = RestaurantsPageResponse(
        page=pagination.page,
        per_page=pagination.per_page,
        total=pagination.total,
        pages=pagination.pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev,
        next_page=pagination.next_num if pagination.has_next else None,
        prev_page=pagination.prev_num if pagination.has_prev else None,
        first_page=1 if pagination.pages else None,
        last_page=pagination.pages or None,
        links=_pagination_links(pagination),
        restaurants=[
            _restaurant_response(restaurant)
            for restaurant in pagination.items
        ],
    )

    return response.model_dump(mode="json"), 200
