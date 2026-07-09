from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import request, url_for
from flask_jwt_extended import current_user
from sqlalchemy.orm import selectinload

from models.order import ORDER_STATUSES, Order
from .schemas import OrdersStatusCountResponse, PaginationLinks


APP_TIMEZONE = timezone(timedelta(hours=-3), name="America/Sao_Paulo")


def validate_status(status):
    if status is None:
        return None
    if status not in ORDER_STATUSES:
        return {"msg": f"status must be one of: {', '.join(ORDER_STATUSES)}"}, 400
    return None


def find_owner_order(order_id):
    return Order.query.options(
        selectinload(Order.customer),
        selectinload(Order.restaurant),
        selectinload(Order.menu_item),
    ).filter_by(id=order_id, owner_id=current_user.id).first()


def localize_datetime(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TIMEZONE)


def resolve_period(query, default_days):
    today = datetime.now(APP_TIMEZONE).date()
    start_date = query.start_date
    end_date = query.end_date

    if start_date and not end_date:
        end_date = today
    elif end_date and not start_date:
        start_date = end_date - timedelta(days=default_days - 1)
    elif not start_date and not end_date:
        end_date = today
        start_date = end_date - timedelta(days=query.days - 1)

    if start_date > end_date:
        return None, None, {"msg": "start_date must be before or equal to end_date"}, 400

    return start_date, end_date, None


def order_in_period(order, start_date, end_date):
    order_date = localize_datetime(order.created_at).date()
    return start_date <= order_date <= end_date


def load_owner_orders():
    return (
        Order.query.options(
            selectinload(Order.customer),
            selectinload(Order.restaurant),
            selectinload(Order.menu_item),
        )
        .filter_by(owner_id=current_user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )


def filter_orders(orders, start_date, end_date, restaurant_id=None, menu_item_id=None, status=None):
    filtered = []
    for order in orders:
        if not order_in_period(order, start_date, end_date):
            continue
        if restaurant_id is not None and order.restaurant_id != restaurant_id:
            continue
        if menu_item_id is not None and order.menu_item_id != menu_item_id:
            continue
        if status is not None and order.status != status:
            continue
        filtered.append(order)
    return filtered


def page_url(endpoint, page, per_page):
    args = request.args.to_dict(flat=True)
    args["page"] = page
    args["per_page"] = per_page
    return url_for(endpoint, **args)


def pagination_links(endpoint, page, pages, per_page):
    first_page = 1 if pages else None
    last_page = pages or None
    return PaginationLinks(
        current=page_url(endpoint, page, per_page),
        first=page_url(endpoint, first_page, per_page) if first_page else None,
        previous=page_url(endpoint, page - 1, per_page) if page > 1 and last_page else None,
        next=page_url(endpoint, page + 1, per_page) if last_page and page < last_page else None,
        last=page_url(endpoint, last_page, per_page) if last_page else None,
    )


def status_counts(orders):
    counts = Counter(order.status for order in orders)
    return [
        OrdersStatusCountResponse(status=status, count=counts.get(status, 0))
        for status in ORDER_STATUSES
    ]
