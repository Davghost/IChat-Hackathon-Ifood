from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import request, url_for
from flask_jwt_extended import current_user

from models.train_record import TrainRecord
from .schemas import OrdersStatusCountResponse, PaginationLinks


APP_TIMEZONE = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
ORDER_STATUS_NEW = "new"
ORDER_STATUS_PREPARING = "preparing"
ORDER_STATUS_READY = "ready"
ORDER_STATUS_DELIVERED = "delivered"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUSES = (
    ORDER_STATUS_NEW,
    ORDER_STATUS_PREPARING,
    ORDER_STATUS_READY,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELLED,
)


def validate_status(status):
    if status is None:
        return None
    if status not in ORDER_STATUSES:
        return {"msg": f"status must be one of: {', '.join(ORDER_STATUSES)}"}, 400
    return None


def find_owner_order(order_id):
    return TrainRecord.query.filter_by(id=order_id, source_table="train").first()


def localize_datetime(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TIMEZONE)


def normalize_train_record(record):
    payload = record.payload or {}
    order_price = float(payload.get("order_price", 0.0) or 0.0)
    quantity = int(payload.get("quantity", 1) or 1)
    order_time = payload.get("order_time") or record.imported_at
    main_dish = str(
        payload.get("main_dish")
        or payload.get("menu_item_name")
        or payload.get("item_name")
        or "Unknown item"
    )
    delivery_neighborhood = payload.get("delivery_neighborhood")
    customer_name = str(
        payload.get("customer_first_name")
        or payload.get("customer_name")
        or payload.get("customer")
        or "Unknown customer"
    )
    status = str(payload.get("status") or ORDER_STATUS_DELIVERED)
    updated_at = payload.get("updated_at") or record.imported_at

    return {
        "id": record.id,
        "order_id": str(record.external_id or payload.get("order_id") or record.id),
        "customer_name": customer_name,
        "customer_email": payload.get("customer_email"),
        "courier_name": payload.get("courier_name"),
        "courier_vehicle": payload.get("courier_vehicle"),
        "restaurant_lat": payload.get("restaurant_lat"),
        "restaurant_lng": payload.get("restaurant_lng"),
        "customer_lat": payload.get("customer_lat"),
        "customer_lng": payload.get("customer_lng"),
        "delivery_neighborhood": str(delivery_neighborhood) if delivery_neighborhood is not None else None,
        "main_dish": main_dish,
        "quantity": quantity,
        "order_price": order_price,
        "total_price": round(order_price * quantity, 2),
        "status": status,
        "order_time": localize_datetime(order_time),
        "updated_at": localize_datetime(updated_at) if updated_at is not None else None,
        "weather": payload.get("weather"),
        "traffic_level": payload.get("traffic_level"),
        "restaurant_busy_level": payload.get("restaurant_busy_level"),
        "app_version": payload.get("app_version"),
        "payload": payload,
    }


def set_train_order_status(record, status):
    payload = dict(record.payload or {})
    payload["status"] = status
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    record.payload = payload
    record.payload_hash = TrainRecord.build_payload_hash(payload)
    return record


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
    order_date = localize_datetime(order["order_time"]).date()
    return start_date <= order_date <= end_date


def load_owner_orders():
    records = (
        TrainRecord.query.filter_by(source_table="train")
        .order_by(TrainRecord.imported_at.desc(), TrainRecord.id.desc())
        .all()
    )
    return [normalize_train_record(record) for record in records]


def filter_orders(orders, start_date, end_date, delivery_neighborhood=None, main_dish=None, status=None):
    filtered = []
    for order in orders:
        if not order_in_period(order, start_date, end_date):
            continue
        if (
            delivery_neighborhood is not None
            and order["delivery_neighborhood"] != delivery_neighborhood
        ):
            continue
        if main_dish is not None and order["main_dish"] != main_dish:
            continue
        if status is not None and order["status"] != status:
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
    counts = Counter(order["status"] for order in orders)
    return [
        OrdersStatusCountResponse(status=status, count=counts.get(status, 0))
        for status in ORDER_STATUSES
    ]
