from datetime import date, datetime

from pydantic import BaseModel, Field


DEFAULT_DASHBOARD_DAYS = 7
MAX_DASHBOARD_DAYS = 30
DEFAULT_ANALYTICS_DAYS = 30
MAX_ANALYTICS_DAYS = 180
DEFAULT_ORDERS_PER_PAGE = 20
MAX_ORDERS_PER_PAGE = 100


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
    delivery_neighborhood: str | None = None
    main_dish: str | None = None
    status: str | None = None


class AnalyticsHistoryQuery(BaseModel):
    days: int = Field(default=DEFAULT_ANALYTICS_DAYS, ge=1, le=MAX_ANALYTICS_DAYS)
    start_date: date | None = None
    end_date: date | None = None
    delivery_neighborhood: str | None = None
    main_dish: str | None = None
    status: str | None = None


class MenuItemCreateMessage(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: float = Field(gt=0)


class MenuItemResponse(BaseModel):
    id: int
    name: str
    price: float
    created_at: datetime


class CreateOwnerOrderMessage(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)
    customer_first_name: str | None = Field(default=None, max_length=120)
    delivery_neighborhood: str | None = Field(default=None, max_length=120)


class OrderStatusUpdateMessage(BaseModel):
    status: str


class OwnerOrderCustomerResponse(BaseModel):
    name: str
    email: str | None = None


class OwnerOrderCourierResponse(BaseModel):
    name: str | None = None
    vehicle: str | None = None


class OwnerOrderLocationResponse(BaseModel):
    lat: float | None = None
    lng: float | None = None


class OwnerOrderRouteResponse(BaseModel):
    restaurant: OwnerOrderLocationResponse
    customer: OwnerOrderLocationResponse


class OwnerOrderContextResponse(BaseModel):
    weather: str | None = None
    traffic_level: str | None = None
    restaurant_busy_level: str | None = None
    app_version: str | None = None


class OwnerOrderResponse(BaseModel):
    id: int
    order_id: str
    customer: OwnerOrderCustomerResponse
    courier: OwnerOrderCourierResponse
    route: OwnerOrderRouteResponse
    context: OwnerOrderContextResponse
    delivery_neighborhood: str | None
    main_dish: str
    quantity: int
    order_price: float
    total_price: float
    status: str
    order_time: datetime
    updated_at: datetime | None
    payload: dict


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
    name: str
    quantity: int
    revenue: float


class DashboardSummaryResponse(BaseModel):
    date: str
    total_orders_today: int
    revenue_today: float
    items_sold_today: int
    average_ticket_today: float
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
