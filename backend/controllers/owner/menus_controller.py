from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from models.menu_item import MenuItem
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from utils.response_schema import GenericResponse
from .access import get_owner_restaurant, owner_required
from .blueprint import owner_controller
from .schemas import MenuItemMessage, MenuItemResponse
from .serializers import menu_item_response


@owner_controller.post("/menus")
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_201=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def create_menu_item():
    # Antes de criar um item, validamos que o token pertence a um owner.
    # O endpoint nao aceita clientes comuns porque o cardapio e um recurso administrativo.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    # O item sempre e criado vinculado ao restaurante atual do owner.
    # Se ainda nao houver restaurante, a operacao nao faz sentido.
    data = request.context.json
    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    # owner_id e restaurant_id sao preenchidos no backend para evitar confianca em ids vindos do cliente.
    menu_item = MenuItem(
        title=data.title,
        name=data.name,
        price=float(data.price),
        description=data.description,
        owner_id=current_user.id,
        restaurant_id=restaurant.id,
    )
    db.session.add(menu_item)
    db.session.commit()

    # O retorno usa serializer proprio para manter o contrato publico uniforme.
    return menu_item_response(menu_item), 201


@owner_controller.get("/menus")
@api.validate(resp=Response(HTTP_200=list[MenuItemResponse], HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def list_menu_items():
    # A listagem e sempre filtrada pelo owner autenticado.
    # Isso garante isolamento entre os cardapios de donos diferentes.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    items = MenuItem.query.filter_by(owner_id=current_user.id).all()
    return [menu_item_response(item) for item in items], 200


@owner_controller.put("/menus/<int:menu_id>")
@api.validate(
    json=MenuItemMessage,
    resp=Response(
        HTTP_200=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def update_menu_item(menu_id):
    # Atualizamos apenas itens pertencentes ao owner autenticado.
    # O menu_id sozinho nao basta; a query valida tambem o owner_id.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    # Reconfirmamos a existencia do restaurante do owner porque o item precisa continuar vinculado a ele.
    data = request.context.json
    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    # Todos os campos editaveis sao substituidos pelo payload validado.
    menu_item.title = data.title
    menu_item.name = data.name
    menu_item.price = float(data.price)
    menu_item.description = data.description
    menu_item.restaurant_id = restaurant.id
    db.session.commit()

    return menu_item_response(menu_item), 200


@owner_controller.delete("/menus/<int:menu_id>")
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def delete_menu_item(menu_id):
    # A exclusao segue a mesma regra de posse da atualizacao:
    # so o dono do item pode remove-lo.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    menu_item = MenuItem.query.filter_by(id=menu_id, owner_id=current_user.id).first()
    if not menu_item:
        return {"msg": "Menu item not found"}, 404

    # A transacao remove o item e responde com mensagem simples para o frontend.
    db.session.delete(menu_item)
    db.session.commit()

    return {"msg": "Menu item deleted successfully"}, 200
