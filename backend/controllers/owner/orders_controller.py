from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from models import MenuItem, TrainRecord
from utils.response_schema import GenericResponse
from .access import owner_required
from .blueprint import owner_controller
from .orders import (
    build_owner_order_payload,
    find_owner_order,
    filter_orders,
    load_owner_orders,
    normalize_train_record,
    pagination_links,
    resolve_period,
    set_train_order_status,
    status_counts,
    validate_status,
)
from .schemas import (
    CreateOwnerOrderMessage,
    DEFAULT_ANALYTICS_DAYS,
    OrderStatusUpdateMessage,
    OwnerOrderResponse,
    OrdersPageResponse,
    OrdersQuery,
)
from .serializers import order_response


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
    # Esta rota consolida consulta, filtro e paginacao dos pedidos do owner.
    # Todas as operacoes partem do conjunto importado em train_records.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    # O objeto query ja chega validado pelo schema OrdersQuery.
    # Isso inclui limites de pagina, janela de datas e filtros opcionais.
    query = request.context.query
    status_error = validate_status(query.status)
    if status_error:
        return status_error

    # Resolve_period transforma a combinacao de days/start_date/end_date em uma janela coerente.
    start_date, end_date, period_error = resolve_period(query, DEFAULT_ANALYTICS_DAYS)
    if period_error:
        return period_error

    # Carregamos os pedidos do owner com relacionamentos necessarios e aplicamos filtros em memoria.
    orders = filter_orders(
        load_owner_orders(),
        start_date,
        end_date,
        delivery_neighborhood=query.delivery_neighborhood,
        main_dish=query.main_dish,
        status=query.status,
    )

    # A paginacao e calculada manualmente porque os filtros atuais dependem do conjunto ja carregado.
    total = len(orders)
    pages = (total + query.per_page - 1) // query.per_page if total else 0
    page = query.page if pages == 0 else min(query.page, pages)
    start_index = (page - 1) * query.per_page
    end_index = start_index + query.per_page
    paged_orders = orders[start_index:end_index]

    # O payload final inclui links de navegacao e a lista serializada dos pedidos reais do dataset.
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


@owner_controller.post("/orders")
@api.validate(
    json=CreateOwnerOrderMessage,
    resp=Response(
        HTTP_201=OwnerOrderResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_403=GenericResponse,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def create_order():
    # Esta rota registra um novo pedido escolhendo um prato ja cadastrado no cardapio do owner.
    # O pedido e salvo em train_records para que painel, historico e faturamento usem a mesma fonte.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    menu_item = MenuItem.query.filter_by(id=data.menu_item_id, owner_id=current_user.id).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    payload = build_owner_order_payload(
        menu_item,
        data.quantity,
        customer_first_name=data.customer_first_name,
        delivery_neighborhood=data.delivery_neighborhood,
        owner_id=current_user.id,
    )
    record = TrainRecord(
        source_table="owner_orders",
        external_id=payload["order_id"],
        payload_hash=TrainRecord.build_payload_hash(payload),
        payload=payload,
    )
    db.session.add(record)
    db.session.commit()

    return order_response(normalize_train_record(record)).model_dump(mode="json"), 201


@owner_controller.patch("/orders/<int:order_id>/status")
@api.validate(
    json=OrderStatusUpdateMessage,
    resp=Response(
        HTTP_200=OwnerOrderResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_403=GenericResponse,
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

    record = find_owner_order(order_id)
    if not record:
        return {"msg": "Order not found"}, 404

    set_train_order_status(record, data.status)
    db.session.commit()
    return order_response(normalize_train_record(record)).model_dump(mode="json"), 200
