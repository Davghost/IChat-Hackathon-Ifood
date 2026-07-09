from factory import api
from flask import request
from flask_jwt_extended import jwt_required
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from .access import owner_required
from .analytics import analytics_history_response, dashboard_response
from .blueprint import owner_controller
from .orders import filter_orders, load_owner_orders, resolve_period, validate_status
from .schemas import (
    AnalyticsHistoryQuery,
    AnalyticsHistoryResponse,
    DEFAULT_ANALYTICS_DAYS,
    DashboardQuery,
    DashboardResponse,
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
    # O dashboard resume o desempenho recente do owner sem expor dados de outros restaurantes.
    # Toda a base do calculo vem dos pedidos associados ao usuario autenticado.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    # dashboard_response concentra a agregacao diaria, receita, ticket medio e top itens.
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
    # Este endpoint entrega historico analitico filtravel por periodo, status e itens.
    # E uma visao mais detalhada que o dashboard, orientada a exploracao do frontend.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    query = request.context.query
    # Validamos o status antes de montar a janela temporal para evitar combinacoes invalidas.
    status_error = validate_status(query.status)
    if status_error:
        return status_error

    start_date, end_date, period_error = resolve_period(query, DEFAULT_ANALYTICS_DAYS)
    if period_error:
        return period_error

    # Os filtros sao aplicados apenas sobre pedidos do owner logado.
    orders = filter_orders(
        load_owner_orders(),
        start_date,
        end_date,
        delivery_neighborhood=query.delivery_neighborhood,
        main_dish=query.main_dish,
        status=query.status,
    )

    # analytics_history_response transforma os pedidos filtrados em resumo e serie temporal.
    response = analytics_history_response(start_date, end_date, orders)
    return response.model_dump(mode="json"), 200
