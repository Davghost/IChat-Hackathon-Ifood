from collections import defaultdict
from datetime import datetime, timedelta

from .orders import (
    APP_TIMEZONE,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_NEW,
    ORDER_STATUS_PREPARING,
    ORDER_STATUS_READY,
    localize_datetime,
)
from .schemas import (
    AnalyticsChartPointResponse,
    AnalyticsHistoryResponse,
    AnalyticsSummaryResponse,
    DashboardChartsResponse,
    DashboardResponse,
    DashboardSummaryResponse,
    OrdersChartPointResponse,
    RevenueChartPointResponse,
    TopMenuItemMetricsResponse,
)


TOP_MENU_ITEMS_LIMIT = 5
WEEKDAY_NAMES = {
    0: "segunda-feira",
    1: "terca-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sabado",
    6: "domingo",
}


def top_menu_item_metrics(grouped_items):
    if not grouped_items:
        return None

    quantity, revenue, menu_item = max(
        grouped_items.values(),
        key=lambda item: (item[0], item[1], item[2]),
    )
    return TopMenuItemMetricsResponse(
        name=menu_item,
        quantity=quantity,
        revenue=round(revenue, 2),
    )


def build_top_menu_items(orders, limit=TOP_MENU_ITEMS_LIMIT):
    grouped = defaultdict(lambda: [0, 0.0, None])
    for order in orders:
        grouped_item = grouped[order["main_dish"]]
        grouped_item[0] += order["quantity"]
        grouped_item[1] += order["total_price"]
        grouped_item[2] = order["main_dish"]

    top_items = sorted(
        grouped.values(),
        key=lambda item: (-item[0], -item[1], item[2]),
    )[:limit]

    return [
        TopMenuItemMetricsResponse(
            name=menu_item,
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
        weekday = localize_datetime(order["order_time"]).weekday()
        revenue_by_weekday[weekday] += order["total_price"]

    best_day = max(revenue_by_weekday.items(), key=lambda item: (item[1], -item[0]))[0]
    return WEEKDAY_NAMES[best_day]


def build_daily_charts(start_date, end_date, orders):
    # O historico analitico deve refletir apenas dias com dados reais.
    # Diferente do dashboard, aqui nao faz sentido preencher lacunas com zero,
    # porque isso infla a serie com pontos artificiais e piora a leitura do frontend.
    points = defaultdict(lambda: [0, 0.0, 0])
    for order in orders:
        order_date = localize_datetime(order["order_time"]).date()
        day_point = points[order_date]
        day_point[0] += 1
        day_point[1] += order["total_price"]
        day_point[2] += order["quantity"]

    return [
        AnalyticsChartPointResponse(
            date=day.isoformat(),
            orders=metrics[0],
            revenue=round(metrics[1], 2),
            items_sold=metrics[2],
        )
        for day, metrics in sorted(points.items())
    ]


def dashboard_response(days, orders):
    now_local = datetime.now(APP_TIMEZONE)
    today = now_local.date()
    start_date = today - timedelta(days=days - 1)
    filtered_orders = [
        order
        for order in orders
        if start_date <= localize_datetime(order["order_time"]).date() <= today
    ]
    today_orders = [
        order for order in filtered_orders if localize_datetime(order["order_time"]).date() == today
    ]

    orders_by_day = {start_date + timedelta(days=index): 0 for index in range(days)}
    revenue_by_day = {start_date + timedelta(days=index): 0.0 for index in range(days)}
    today_top_items = defaultdict(lambda: [0, 0.0, None])

    for order in filtered_orders:
        order_date = localize_datetime(order["order_time"]).date()
        orders_by_day[order_date] += 1
        revenue_by_day[order_date] += order["total_price"]

        if order_date == today:
            today_item = today_top_items[order["main_dish"]]
            today_item[0] += order["quantity"]
            today_item[1] += order["total_price"]
            today_item[2] = order["main_dish"]

    revenue_today = round(sum(order["total_price"] for order in today_orders), 2)
    items_sold_today = sum(order["quantity"] for order in today_orders)
    pending_orders_today = sum(
        1
        for order in today_orders
        if order["status"] in (ORDER_STATUS_NEW, ORDER_STATUS_PREPARING, ORDER_STATUS_READY)
    )
    completed_orders_today = sum(
        1 for order in today_orders if order["status"] == ORDER_STATUS_DELIVERED
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
    total_revenue = round(sum(order["total_price"] for order in orders), 2)
    total_orders = len(orders)
    items_sold = sum(order["quantity"] for order in orders)
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
