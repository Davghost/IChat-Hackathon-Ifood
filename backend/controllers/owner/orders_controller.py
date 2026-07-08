from factory import api, db
from flask import request
from flask_jwt_extended import jwt_required
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from utils.response_schema import GenericResponse
from .common import (
    DEFAULT_ANALYTICS_DAYS,
    OrderStatusUpdateMessage,
    OwnerOrderResponse,
    OrdersPageResponse,
    OrdersQuery,
    filter_orders,
    find_owner_order,
    load_owner_orders,
    order_response,
    owner_controller,
    owner_required,
    pagination_links,
    resolve_period,
    status_counts,
    validate_status,
)


@owner_controller.get("/orders")
@api.validate(
    query=OrdersQuery,
    resp=Response(
        HTTP_200=OrdersPageResponse,
        HTTP_400=SpectreeValidationError,
    ),
    tags=["owner"],
)
@jwt_required()
def list_orders():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    status_error = validate_status(query.status)
    if status_error:
        return status_error

    start_date, end_date, period_error = resolve_period(query, DEFAULT_ANALYTICS_DAYS)
    if period_error:
        return period_error

    orders = filter_orders(
        load_owner_orders(),
        start_date,
        end_date,
        restaurant_id=query.restaurant_id,
        menu_item_id=query.menu_item_id,
        status=query.status,
    )

    total = len(orders)
    pages = (total + query.per_page - 1) // query.per_page if total else 0
    page = query.page if pages == 0 else min(query.page, pages)
    start_index = (page - 1) * query.per_page
    end_index = start_index + query.per_page
    paged_orders = orders[start_index:end_index]

    response = OrdersPageResponse(
        page=page,
        per_page=query.per_page,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1 and pages > 0,
        next_page=page + 1 if page < pages else None,
        prev_page=page - 1 if page > 1 and pages > 0 else None,
        links=pagination_links("owner_controller.list_orders", page, pages, query.per_page),
        status_counts=status_counts(orders),
        orders=[order_response(order) for order in paged_orders],
    )
    return response.model_dump(mode="json"), 200


@owner_controller.patch("/orders/<int:order_id>/status")
@api.validate(
    json=OrderStatusUpdateMessage,
    resp=Response(
        HTTP_200=OwnerOrderResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def update_order_status(order_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    status_error = validate_status(data.status)
    if status_error:
        return status_error

    order = find_owner_order(order_id)
    if not order:
        return {"msg": "Order not found"}, 404

    order.status = data.status
    db.session.commit()
    return order_response(order).model_dump(mode="json"), 200
