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
PRESET_AI_QUESTIONS = [
    {
        "question": "Quanto eu faturei nas ultimas 4 semanas?",
        "description": "Soma o faturamento recente do restaurante.",
    },
    {
        "question": "Qual prato mais vendeu no mes passado?",
        "description": "Aponta o item com maior volume vendido no mes anterior.",
    },
    {
        "question": "Qual dia da semana vende melhor?",
        "description": "Mostra o melhor dia historico em receita.",
    },
    {
        "question": "Quanto devo vender amanha?",
        "description": "Entrega uma previsao simples de faturamento.",
    },
    {
        "question": "Quantos pedidos devo receber amanha?",
        "description": "Entrega uma previsao simples de demanda.",
    },
]


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
    per_page: int = Field(
        default=DEFAULT_ORDERS_PER_PAGE,
        ge=1,
        le=MAX_ORDERS_PER_PAGE,
    )
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


class AssistantChatMessage(BaseModel):
    question: str
    restaurant_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None


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


class AssistantTemplateResponse(BaseModel):
    question: str
    description: str


class AssistantTemplatesResponse(BaseModel):
    questions: list[AssistantTemplateResponse]


class AssistantAnswerResponse(BaseModel):
    question: str
    answer: str
    source: str
    used_fallback: bool
    supporting_metrics: dict[str, str]


class ForecastPointResponse(BaseModel):
    date: str
    predicted_revenue: float
    predicted_orders: int
    predicted_items_sold: int


class ForecastResponse(BaseModel):
    source: str
    used_fallback: bool
    period_days: int
    generated_at: datetime
    explanation: str
    forecasts: list[ForecastPointResponse]


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


def ai_service_request(path, payload):
    request_url = f"{current_app.config['AI_SERVICE_BASE_URL'].rstrip('/')}{path}"
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


def forecast_response(days, orders, restaurant_id=None):
    history = []
    for order in orders:
        order_date = localize_datetime(order.created_at).date()
        if restaurant_id is not None and order.restaurant_id != restaurant_id:
            continue
        history.append(
            {
                "date": order_date.isoformat(),
                "revenue": order.total_price,
                "orders": 1,
                "items_sold": order.quantity,
            }
        )

    payload = {
        "owner_id": current_user.id,
        "restaurant_id": restaurant_id,
        "days": days,
        "history": history,
    }
    external_response = ai_service_request("/forecast", payload)
    if external_response and isinstance(external_response.get("forecasts"), list):
        forecasts = [
            ForecastPointResponse(
                date=item["date"],
                predicted_revenue=round(float(item["predicted_revenue"]), 2),
                predicted_orders=int(item["predicted_orders"]),
                predicted_items_sold=int(item["predicted_items_sold"]),
            )
            for item in external_response["forecasts"]
        ]
        return ForecastResponse(
            source="external",
            used_fallback=False,
            period_days=days,
            generated_at=datetime.now(APP_TIMEZONE),
            explanation=external_response.get(
                "explanation",
                "Previsao retornada pelo servico de machine learning externo.",
            ),
            forecasts=forecasts,
        )

    forecasts = same_weekday_forecast_points(orders, days, restaurant_id=restaurant_id)
    return ForecastResponse(
        source="local_fallback",
        used_fallback=True,
        period_days=days,
        generated_at=datetime.now(APP_TIMEZONE),
        explanation=(
            "Previsao local baseada na media dos mesmos dias da semana e, "
            "na falta deles, na media recente do historico."
        ),
        forecasts=forecasts,
    )


def previous_month_range(reference_date):
    first_day_current_month = reference_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    return first_day_previous_month, last_day_previous_month


def assistant_fallback_answer(question, orders, restaurant_id=None, start_date=None, end_date=None):
    normalized_question = question.strip().lower()
    today = datetime.now(APP_TIMEZONE).date()
    filtered_orders = orders
    if restaurant_id is not None:
        filtered_orders = [order for order in filtered_orders if order.restaurant_id == restaurant_id]

    if start_date and end_date:
        filtered_orders = [
            order for order in filtered_orders if order_in_period(order, start_date, end_date)
        ]

    if "ultimas 4 semanas" in normalized_question or "ultimas quatro semanas" in normalized_question:
        period_start = today - timedelta(days=27)
        period_orders = [
            order for order in filtered_orders if order_in_period(order, period_start, today)
        ]
        revenue = round(sum(order.total_price for order in period_orders), 2)
        return AssistantAnswerResponse(
            question=question,
            answer=f"Seu faturamento nas ultimas 4 semanas foi de R$ {revenue:.2f}.",
            source="local_fallback",
            used_fallback=True,
            supporting_metrics={
                "start_date": period_start.isoformat(),
                "end_date": today.isoformat(),
                "total_revenue": f"{revenue:.2f}",
            },
        )

    if "mes passado" in normalized_question and ("prato" in normalized_question or "comida" in normalized_question):
        period_start, period_end = previous_month_range(today)
        period_orders = [
            order for order in filtered_orders if order_in_period(order, period_start, period_end)
        ]
        top_items = build_top_menu_items(period_orders, limit=1)
        if not top_items:
            answer = "Nao houve vendas no mes passado para calcular o prato mais vendido."
            metrics = {"start_date": period_start.isoformat(), "end_date": period_end.isoformat()}
        else:
            item = top_items[0]
            answer = (
                f"No mes passado, o prato mais vendido foi {item.name}, com "
                f"{item.quantity} unidades e R$ {item.revenue:.2f} em receita."
            )
            metrics = {
                "start_date": period_start.isoformat(),
                "end_date": period_end.isoformat(),
                "top_menu_item": item.name,
                "quantity": str(item.quantity),
                "revenue": f"{item.revenue:.2f}",
            }

        return AssistantAnswerResponse(
            question=question,
            answer=answer,
            source="local_fallback",
            used_fallback=True,
            supporting_metrics=metrics,
        )

    if "dia da semana" in normalized_question and "vende melhor" in normalized_question:
        top_weekday = best_weekday(filtered_orders)
        answer = (
            f"O melhor dia da semana em receita e {top_weekday}."
            if top_weekday
            else "Ainda nao ha vendas suficientes para identificar o melhor dia da semana."
        )
        return AssistantAnswerResponse(
            question=question,
            answer=answer,
            source="local_fallback",
            used_fallback=True,
            supporting_metrics={"best_weekday": top_weekday or ""},
        )

    if "quanto devo vender amanha" in normalized_question or (
        "amanha" in normalized_question and "fatur" in normalized_question
    ):
        forecast = forecast_response(1, orders, restaurant_id=restaurant_id)
        point = forecast.forecasts[0]
        return AssistantAnswerResponse(
            question=question,
            answer=(
                f"A previsao para amanha e faturar R$ {point.predicted_revenue:.2f}, "
                f"com cerca de {point.predicted_orders} pedidos."
            ),
            source=forecast.source,
            used_fallback=forecast.used_fallback,
            supporting_metrics={
                "date": point.date,
                "predicted_revenue": f"{point.predicted_revenue:.2f}",
                "predicted_orders": str(point.predicted_orders),
            },
        )

    if "quantos pedidos devo receber amanha" in normalized_question or (
        "amanha" in normalized_question and "pedido" in normalized_question
    ):
        forecast = forecast_response(1, orders, restaurant_id=restaurant_id)
        point = forecast.forecasts[0]
        return AssistantAnswerResponse(
            question=question,
            answer=(
                f"A previsao para amanha e receber {point.predicted_orders} pedidos "
                f"e vender cerca de {point.predicted_items_sold} itens."
            ),
            source=forecast.source,
            used_fallback=forecast.used_fallback,
            supporting_metrics={
                "date": point.date,
                "predicted_orders": str(point.predicted_orders),
                "predicted_items_sold": str(point.predicted_items_sold),
            },
        )

    return AssistantAnswerResponse(
        question=question,
        answer=(
            "Consigo responder melhor perguntas sobre faturamento recente, prato mais vendido, "
            "melhor dia da semana e previsoes para amanha."
        ),
        source="local_fallback",
        used_fallback=True,
        supporting_metrics={"templates": ", ".join(item["question"] for item in PRESET_AI_QUESTIONS)},
    )


def assistant_response(question, orders, restaurant_id=None, start_date=None, end_date=None):
    payload = {
        "question": question,
        "owner_id": current_user.id,
        "restaurant_id": restaurant_id,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "templates": PRESET_AI_QUESTIONS,
    }
    external_response = ai_service_request("/chat", payload)
    if external_response and external_response.get("answer"):
        supporting_metrics = {
            str(key): str(value)
            for key, value in external_response.get("supporting_metrics", {}).items()
        }
        return AssistantAnswerResponse(
            question=question,
            answer=external_response["answer"],
            source="external",
            used_fallback=False,
            supporting_metrics=supporting_metrics,
        )

    return assistant_fallback_answer(
        question,
        orders,
        restaurant_id=restaurant_id,
        start_date=start_date,
        end_date=end_date,
    )
