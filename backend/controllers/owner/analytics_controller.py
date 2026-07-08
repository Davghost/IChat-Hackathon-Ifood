from factory import api
from flask import request
from flask_jwt_extended import jwt_required
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from utils.response_schema import GenericResponse
from .common import (
    AnalyticsHistoryQuery,
    AnalyticsHistoryResponse,
    AIPlaceholdersResponse,
    DEFAULT_ANALYTICS_DAYS,
    DashboardQuery,
    DashboardResponse,
    ForecastQuery,
    ForecastResponse,
    analytics_history_response,
    dashboard_response,
    filter_orders,
    find_owner_restaurant,
    forecast_response,
    load_owner_orders,
    owner_ai_placeholders_response,
    owner_controller,
    owner_required,
    resolve_period,
    validate_status,
)


@owner_controller.get("/dashboard")
@api.validate(
    query=DashboardQuery,
    resp=Response(
        HTTP_200=DashboardResponse,
        HTTP_400=SpectreeValidationError,
    ),
    tags=["owner"],
)
@jwt_required()
def get_dashboard():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    response = dashboard_response(query.days, load_owner_orders())
    return response.model_dump(mode="json"), 200


@owner_controller.get("/analytics/history")
@api.validate(
    query=AnalyticsHistoryQuery,
    resp=Response(
        HTTP_200=AnalyticsHistoryResponse,
        HTTP_400=SpectreeValidationError,
    ),
    tags=["owner"],
)
@jwt_required()
def get_analytics_history():
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
    response = analytics_history_response(start_date, end_date, orders)
    return response.model_dump(mode="json"), 200


@owner_controller.get("/ai/placeholders")
@api.validate(
    query=AnalyticsHistoryQuery,
    resp=Response(
        HTTP_200=AIPlaceholdersResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def get_ai_placeholders():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    if query.restaurant_id is not None and not find_owner_restaurant(query.restaurant_id):
        return {"msg": "Restaurant not found"}, 404

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
    response = owner_ai_placeholders_response(
        start_date,
        end_date,
        orders,
        restaurant_id=query.restaurant_id,
    )
    return response.model_dump(mode="json"), 200


@owner_controller.get("/forecasts")
@api.validate(
    query=ForecastQuery,
    resp=Response(
        HTTP_200=ForecastResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def get_forecasts():
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    if query.restaurant_id is not None and not find_owner_restaurant(query.restaurant_id):
        return {"msg": "Restaurant not found"}, 404

    response = forecast_response(
        query.days,
        load_owner_orders(),
        restaurant_id=query.restaurant_id,
    )
    return response.model_dump(mode="json"), 200
