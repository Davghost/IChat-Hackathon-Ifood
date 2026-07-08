from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import Blueprint, current_app, request, url_for
from flask_jwt_extended import current_user
from models.menu_item import MenuItem
from models.order import (
    ORDER_STATUSES,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_NEW,
    ORDER_STATUS_PREPARING,
    ORDER_STATUS_READY,
    Order,
)
from models.restaurant import Restaurant
from models.user import User
from pydantic import BaseModel, Field
from sqlalchemy.orm import selectinload

owner_controller = Blueprint("owner_controller", __name__, url_prefix="/api/owner")

DEFAULT_DASHBOARD_DAYS = 7
MAX_DASHBOARD_DAYS = 30
DEFAULT_ANALYTICS_DAYS = 30
MAX_ANALYTICS_DAYS = 180
DEFAULT_ORDERS_PER_PAGE = 20
MAX_ORDERS_PER_PAGE = 100
DEFAULT_FORECAST_DAYS = 7
MAX_FORECAST_DAYS = 14
TOP_MENU_ITEMS_LIMIT = 5
AI_SERVICE_TIMEOUT_SECONDS = 2
AI_FORECAST_PATH = "/forecast"
AI_PLACEHOLDER_PATH = "/placeholders/owner-insights"
AI_PLACEHOLDER_NOTE = (
    "PLACEHOLDER: payload e estrutura preparados para a futura IA em http://localhost:8000."
)
APP_TIMEZONE = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
WEEKDAY_NAMES = {
    0: "segunda-feira",
    1: "terca-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sabado",
    6: "domingo",
}


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


class MenuItemResponse(BaseModel):
    id: int
    title: str
    name: str
    price: float
    description: str
    restaurant_id: int


class PaginationLinks(BaseModel):
    current: str
    first: str | None
    previous: str | None
    next: str | None
    last: str | None


class DashboardQuery(BaseModel):
    days: int = Field(default=DEFAULT_DASHBOARD_DAYS, ge=1, le=MAX_DASHBOARD_DAYS)


class OrdersQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=DEFAULT_ORDERS_PER_PAGE, ge=1, le=MAX_ORDERS_PER_PAGE)
    days: int = Field(default=DEFAULT_ANALYTICS_DAYS, ge=1, le=MAX_ANALYTICS_DAYS)
    start_date: date | None = None
    end_date: date | None = None
    restaurant_id: int | None = None
    menu_item_id: int | None = None
    status: str | None = None


class AnalyticsHistoryQuery(BaseModel):
    days: int = Field(default=DEFAULT_ANALYTICS_DAYS, ge=1, le=MAX_ANALYTICS_DAYS)
    start_date: date | None = None
    end_date: date | None = None
    restaurant_id: int | None = None
    menu_item_id: int | None = None
    status: str | None = None


class ForecastQuery(BaseModel):
    days: int = Field(default=DEFAULT_FORECAST_DAYS, ge=1, le=MAX_FORECAST_DAYS)
    restaurant_id: int | None = None


class OrderStatusUpdateMessage(BaseModel):
    status: str


class OwnerOrderCustomerResponse(BaseModel):
    id: int
    username: str
    email: str


class OwnerOrderRestaurantResponse(BaseModel):
    id: int
    name: str


class OwnerOrderMenuItemResponse(BaseModel):
    id: int
    title: str
    name: str


class OwnerOrderResponse(BaseModel):
    id: int
    customer: OwnerOrderCustomerResponse
    restaurant: OwnerOrderRestaurantResponse
    menu_item: OwnerOrderMenuItemResponse
    quantity: int
    unit_price: float
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime


class OrdersStatusCountResponse(BaseModel):
    status: str
    count: int


class OrdersPageResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
    next_page: int | None
    prev_page: int | None
    links: PaginationLinks
    status_counts: list[OrdersStatusCountResponse]
    orders: list[OwnerOrderResponse]


class TopMenuItemMetricsResponse(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    revenue: float


class DashboardSummaryResponse(BaseModel):
    date: str
    total_orders_today: int
    revenue_today: float
    items_sold_today: int
    average_ticket_today: float
    pending_orders_today: int
    completed_orders_today: int
    most_ordered_item: TopMenuItemMetricsResponse | None


class OrdersChartPointResponse(BaseModel):
    date: str
    orders: int


class RevenueChartPointResponse(BaseModel):
    date: str
    revenue: float


class DashboardChartsResponse(BaseModel):
    orders_by_day: list[OrdersChartPointResponse]
    revenue_by_day: list[RevenueChartPointResponse]
    top_menu_items: list[TopMenuItemMetricsResponse]


class DashboardResponse(BaseModel):
    period_days: int
    generated_at: datetime
    summary: DashboardSummaryResponse
    charts: DashboardChartsResponse


class AnalyticsSummaryResponse(BaseModel):
    start_date: str
    end_date: str
    total_orders: int
    total_revenue: float
    items_sold: int
    average_ticket: float
    best_weekday: str | None
    top_menu_item: TopMenuItemMetricsResponse | None


class AnalyticsChartPointResponse(BaseModel):
    date: str
    orders: int
    revenue: float
    items_sold: int


class AnalyticsHistoryResponse(BaseModel):
    generated_at: datetime
    summary: AnalyticsSummaryResponse
    charts: list[AnalyticsChartPointResponse]
    top_menu_items: list[TopMenuItemMetricsResponse]


class ForecastPointResponse(BaseModel):
    date: str
    predicted_revenue: float
    predicted_orders: int
    predicted_items_sold: int


class ForecastResponse(BaseModel):
    source: str
    source_url: str
    used_fallback: bool
    period_days: int
    generated_at: datetime
    explanation: str
    placeholder_note: str | None = None
    forecasts: list[ForecastPointResponse]


class AIPlaceholderMetricResponse(BaseModel):
    label: str
    value: str
    placeholder_note: str


class AIPlaceholderInsightResponse(BaseModel):
    title: str
    description: str
    placeholder_note: str


class AIPlaceholdersResponse(BaseModel):
    source: str
    source_url: str
    generated_at: datetime
    placeholder_note: str
    metrics: list[AIPlaceholderMetricResponse]
    insights: list[AIPlaceholderInsightResponse]


def owner_required():
    if not isinstance(current_user, User) or current_user.role != "owner":
        return {"msg": "Only owners can manage restaurants and menus"}, 403
    return None


def validate_status(status):
    if status is None:
        return None
    if status not in ORDER_STATUSES:
        return {"msg": f"status must be one of: {', '.join(ORDER_STATUSES)}"}, 400
    return None


def find_owner_restaurant(restaurant_id):
    return Restaurant.query.filter_by(id=restaurant_id, owner_id=current_user.id).first()


def get_owner_restaurant():
    return Restaurant.query.filter_by(owner_id=current_user.id).first()


def find_owner_order(order_id):
    return Order.query.options(
        selectinload(Order.customer),
        selectinload(Order.restaurant),
        selectinload(Order.menu_item),
    ).filter_by(id=order_id, owner_id=current_user.id).first()


def restaurant_response(restaurant):
    return RestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        description=restaurant.description,
    ).model_dump()


def menu_item_response(menu_item):
    return MenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
        restaurant_id=menu_item.restaurant_id,
    ).model_dump()


def order_response(order):
    return OwnerOrderResponse(
        id=order.id,
        customer=OwnerOrderCustomerResponse(
            id=order.customer.id,
            username=order.customer.username,
            email=order.customer.email,
        ),
        restaurant=OwnerOrderRestaurantResponse(
            id=order.restaurant.id,
            name=order.restaurant.name,
        ),
        menu_item=OwnerOrderMenuItemResponse(
            id=order.menu_item.id,
            title=order.menu_item.title,
            name=order.menu_item.name,
        ),
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


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


def top_menu_item_metrics(grouped_items):
    if not grouped_items:
        return None

    quantity, revenue, menu_item = max(
        grouped_items.values(),
        key=lambda item: (item[0], item[1], item[2].name),
    )
    return TopMenuItemMetricsResponse(
        menu_item_id=menu_item.id,
        name=menu_item.name,
        quantity=quantity,
        revenue=round(revenue, 2),
    )


def build_top_menu_items(orders, limit=TOP_MENU_ITEMS_LIMIT):
    grouped = defaultdict(lambda: [0, 0.0, None])
    for order in orders:
        grouped_item = grouped[order.menu_item_id]
        grouped_item[0] += order.quantity
        grouped_item[1] += order.total_price
        grouped_item[2] = order.menu_item

    top_items = sorted(
        grouped.values(),
        key=lambda item: (-item[0], -item[1], item[2].name),
    )[:limit]

    return [
        TopMenuItemMetricsResponse(
            menu_item_id=menu_item.id,
            name=menu_item.name,
            quantity=quantity,
            revenue=round(revenue, 2),
        )
        for quantity, revenue, menu_item in top_items
    ]


def best_weekday(orders):
    if not orders:
        return None

    revenue_by_weekday = defaultdict(float)
    for order in orders:
        weekday = localize_datetime(order.created_at).weekday()
        revenue_by_weekday[weekday] += order.total_price

    best_day = max(revenue_by_weekday.items(), key=lambda item: (item[1], -item[0]))[0]
    return WEEKDAY_NAMES[best_day]


def build_daily_charts(start_date, end_date, orders):
    points = {
        start_date + timedelta(days=index): [0, 0.0, 0]
        for index in range((end_date - start_date).days + 1)
    }
    for order in orders:
        order_date = localize_datetime(order.created_at).date()
        day_point = points[order_date]
        day_point[0] += 1
        day_point[1] += order.total_price
        day_point[2] += order.quantity

    return [
        AnalyticsChartPointResponse(
            date=day.isoformat(),
            orders=metrics[0],
            revenue=round(metrics[1], 2),
            items_sold=metrics[2],
        )
        for day, metrics in points.items()
    ]


def dashboard_response(days, orders):
    now_local = datetime.now(APP_TIMEZONE)
    today = now_local.date()
    start_date = today - timedelta(days=days - 1)
    filtered_orders = [order for order in orders if order_in_period(order, start_date, today)]
    today_orders = [
        order for order in filtered_orders if localize_datetime(order.created_at).date() == today
    ]

    orders_by_day = {start_date + timedelta(days=index): 0 for index in range(days)}
    revenue_by_day = {start_date + timedelta(days=index): 0.0 for index in range(days)}
    today_top_items = defaultdict(lambda: [0, 0.0, None])

    for order in filtered_orders:
        order_date = localize_datetime(order.created_at).date()
        orders_by_day[order_date] += 1
        revenue_by_day[order_date] += order.total_price

        if order_date == today:
            today_item = today_top_items[order.menu_item_id]
            today_item[0] += order.quantity
            today_item[1] += order.total_price
            today_item[2] = order.menu_item

    revenue_today = round(sum(order.total_price for order in today_orders), 2)
    items_sold_today = sum(order.quantity for order in today_orders)
    pending_orders_today = sum(
        1
        for order in today_orders
        if order.status in (ORDER_STATUS_NEW, ORDER_STATUS_PREPARING, ORDER_STATUS_READY)
    )
    completed_orders_today = sum(
        1 for order in today_orders if order.status == ORDER_STATUS_DELIVERED
    )

    return DashboardResponse(
        period_days=days,
        generated_at=now_local,
        summary=DashboardSummaryResponse(
            date=today.isoformat(),
            total_orders_today=len(today_orders),
            revenue_today=revenue_today,
            items_sold_today=items_sold_today,
            average_ticket_today=round(revenue_today / len(today_orders), 2) if today_orders else 0.0,
            pending_orders_today=pending_orders_today,
            completed_orders_today=completed_orders_today,
            most_ordered_item=top_menu_item_metrics(today_top_items),
        ),
        charts=DashboardChartsResponse(
            orders_by_day=[
                OrdersChartPointResponse(date=day.isoformat(), orders=orders_by_day[day])
                for day in orders_by_day
            ],
            revenue_by_day=[
                RevenueChartPointResponse(date=day.isoformat(), revenue=round(revenue_by_day[day], 2))
                for day in revenue_by_day
            ],
            top_menu_items=build_top_menu_items(filtered_orders),
        ),
    )


def analytics_history_response(start_date, end_date, orders):
    total_revenue = round(sum(order.total_price for order in orders), 2)
    total_orders = len(orders)
    items_sold = sum(order.quantity for order in orders)
    top_items = build_top_menu_items(orders)

    return AnalyticsHistoryResponse(
        generated_at=datetime.now(APP_TIMEZONE),
        summary=AnalyticsSummaryResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_orders=total_orders,
            total_revenue=total_revenue,
            items_sold=items_sold,
            average_ticket=round(total_revenue / total_orders, 2) if total_orders else 0.0,
            best_weekday=best_weekday(orders),
            top_menu_item=top_items[0] if top_items else None,
        ),
        charts=build_daily_charts(start_date, end_date, orders),
        top_menu_items=top_items,
    )


def ai_service_base_url():
    return current_app.config["AI_SERVICE_BASE_URL"].rstrip("/")


def ai_service_request(path, payload):
    request_url = f"{ai_service_base_url()}{path}"
    body = json.dumps(payload).encode("utf-8")
    http_request = urllib_request.Request(
        request_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(http_request, timeout=AI_SERVICE_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def build_orders_history(orders, restaurant_id=None):
    history = []
    for order in orders:
        if restaurant_id is not None and order.restaurant_id != restaurant_id:
            continue
        order_date = localize_datetime(order.created_at).date()
        history.append(
            {
                "date": order_date.isoformat(),
                "revenue": round(order.total_price, 2),
                "orders": 1,
                "items_sold": order.quantity,
                "menu_item": order.menu_item.name,
                "status": order.status,
            }
        )
    return history


def same_weekday_forecast_points(orders, days, restaurant_id=None):
    today = datetime.now(APP_TIMEZONE).date()
    filtered_orders = orders
    if restaurant_id is not None:
        filtered_orders = [order for order in filtered_orders if order.restaurant_id == restaurant_id]

    historical_daily = defaultdict(lambda: [0, 0.0, 0])
    for order in filtered_orders:
        order_date = localize_datetime(order.created_at).date()
        day_metrics = historical_daily[order_date]
        day_metrics[0] += 1
        day_metrics[1] += order.total_price
        day_metrics[2] += order.quantity

    forecasts = []
    for offset in range(1, days + 1):
        forecast_date = today + timedelta(days=offset)
        matching_days = []
        lookback_day = forecast_date - timedelta(days=7)
        while len(matching_days) < 4 and lookback_day in historical_daily:
            matching_days.append(historical_daily[lookback_day])
            lookback_day -= timedelta(days=7)

        if not matching_days:
            fallback_history = list(historical_daily.values())[-14:]
            matching_days = fallback_history or [[0, 0.0, 0]]

        predicted_orders = round(sum(day[0] for day in matching_days) / len(matching_days))
        predicted_revenue = round(sum(day[1] for day in matching_days) / len(matching_days), 2)
        predicted_items_sold = round(sum(day[2] for day in matching_days) / len(matching_days))

        forecasts.append(
            ForecastPointResponse(
                date=forecast_date.isoformat(),
                predicted_revenue=predicted_revenue,
                predicted_orders=predicted_orders,
                predicted_items_sold=predicted_items_sold,
            )
        )

    return forecasts


def normalize_forecast_points(items):
    normalized = []
    for item in items:
        normalized.append(
            ForecastPointResponse(
                date=str(item["date"]),
                predicted_revenue=round(float(item["predicted_revenue"]), 2),
                predicted_orders=int(item["predicted_orders"]),
                predicted_items_sold=int(item["predicted_items_sold"]),
            )
        )
    return normalized


def forecast_response(days, orders, restaurant_id=None):
    request_url = f"{ai_service_base_url()}{AI_FORECAST_PATH}"
    payload = {
        "owner_id": current_user.id,
        "restaurant_id": restaurant_id,
        "days": days,
        "history": build_orders_history(orders, restaurant_id=restaurant_id),
        "placeholder": True,
        "placeholder_note": AI_PLACEHOLDER_NOTE,
    }
    external_response = ai_service_request(AI_FORECAST_PATH, payload)
    if external_response and isinstance(external_response.get("forecasts"), list):
        return ForecastResponse(
            source="external_placeholder",
            source_url=request_url,
            used_fallback=False,
            period_days=days,
            generated_at=datetime.now(APP_TIMEZONE),
            explanation=external_response.get(
                "explanation",
                "PLACEHOLDER: previsao retornada pela integracao temporaria da IA.",
            ),
            placeholder_note=AI_PLACEHOLDER_NOTE,
            forecasts=normalize_forecast_points(external_response["forecasts"]),
        )

    return ForecastResponse(
        source="local_placeholder_fallback",
        source_url=request_url,
        used_fallback=True,
        period_days=days,
        generated_at=datetime.now(APP_TIMEZONE),
        explanation=(
            "PLACEHOLDER: integracao futura indisponivel em http://localhost:8000; "
            "foi usada uma previsao local baseada no historico."
        ),
        placeholder_note=AI_PLACEHOLDER_NOTE,
        forecasts=same_weekday_forecast_points(orders, days, restaurant_id=restaurant_id),
    )


def summary_snapshot(summary):
    return {
        "total_orders": summary.total_orders,
        "total_revenue": round(summary.total_revenue, 2),
        "items_sold": summary.items_sold,
        "average_ticket": round(summary.average_ticket, 2),
        "best_weekday": summary.best_weekday or "",
        "top_menu_item": summary.top_menu_item.name if summary.top_menu_item else "",
    }


def build_placeholder_metrics(summary):
    top_item_name = summary.top_menu_item.name if summary.top_menu_item else "Sem dados"
    best_day = summary.best_weekday or "Sem dados"

    return [
        AIPlaceholderMetricResponse(
            label="PLACEHOLDER: faturamento do periodo",
            value=f"R$ {summary.total_revenue:.2f}",
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
        AIPlaceholderMetricResponse(
            label="PLACEHOLDER: ticket medio sugerido pela IA",
            value=f"R$ {summary.average_ticket:.2f}",
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
        AIPlaceholderMetricResponse(
            label="PLACEHOLDER: item em destaque",
            value=top_item_name,
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
        AIPlaceholderMetricResponse(
            label="PLACEHOLDER: melhor dia para campanha",
            value=best_day,
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
    ]


def build_placeholder_insights(summary):
    top_item_name = summary.top_menu_item.name if summary.top_menu_item else "um item sem historico"
    best_day = summary.best_weekday or "um dia ainda nao identificado"

    return [
        AIPlaceholderInsightResponse(
            title="PLACEHOLDER: oportunidade comercial",
            description=(
                f"A futura IA pode recomendar promocao para {top_item_name} "
                f"com base no faturamento atual de R$ {summary.total_revenue:.2f}."
            ),
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
        AIPlaceholderInsightResponse(
            title="PLACEHOLDER: planejamento operacional",
            description=(
                f"A futura IA pode sugerir reforco de equipe em {best_day} "
                f"e revisar ticket medio atual de R$ {summary.average_ticket:.2f}."
            ),
            placeholder_note=AI_PLACEHOLDER_NOTE,
        ),
    ]


def normalize_placeholder_metrics(items):
    normalized = []
    for item in items:
        normalized.append(
            AIPlaceholderMetricResponse(
                label=str(item.get("label", "PLACEHOLDER: metrica sem titulo")),
                value=str(item.get("value", "")),
                placeholder_note=str(item.get("placeholder_note", AI_PLACEHOLDER_NOTE)),
            )
        )
    return normalized


def normalize_placeholder_insights(items):
    normalized = []
    for item in items:
        normalized.append(
            AIPlaceholderInsightResponse(
                title=str(item.get("title", "PLACEHOLDER: insight sem titulo")),
                description=str(item.get("description", "")),
                placeholder_note=str(item.get("placeholder_note", AI_PLACEHOLDER_NOTE)),
            )
        )
    return normalized


def owner_ai_placeholders_response(start_date, end_date, orders, restaurant_id=None):
    analytics = analytics_history_response(start_date, end_date, orders)
    request_url = f"{ai_service_base_url()}{AI_PLACEHOLDER_PATH}"
    payload = {
        "owner_id": current_user.id,
        "restaurant_id": restaurant_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "history": build_orders_history(orders, restaurant_id=restaurant_id),
        "summary": summary_snapshot(analytics.summary),
        "placeholder": True,
        "placeholder_note": AI_PLACEHOLDER_NOTE,
    }
    external_response = ai_service_request(AI_PLACEHOLDER_PATH, payload)
    if external_response:
        return AIPlaceholdersResponse(
            source="external_placeholder",
            source_url=request_url,
            generated_at=datetime.now(APP_TIMEZONE),
            placeholder_note=str(external_response.get("placeholder_note", AI_PLACEHOLDER_NOTE)),
            metrics=normalize_placeholder_metrics(external_response.get("metrics", [])),
            insights=normalize_placeholder_insights(external_response.get("insights", [])),
        )

    return AIPlaceholdersResponse(
        source="local_placeholder_fallback",
        source_url=request_url,
        generated_at=datetime.now(APP_TIMEZONE),
        placeholder_note=AI_PLACEHOLDER_NOTE,
        metrics=build_placeholder_metrics(analytics.summary),
        insights=build_placeholder_insights(analytics.summary),
    )
