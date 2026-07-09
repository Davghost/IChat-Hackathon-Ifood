from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from spectree import Response
from spectree.models import ValidationError as SpectreeValidationError

from models import MenuItem
from utils.response_schema import GenericResponse
from .access import owner_required
from .blueprint import owner_controller
from .schemas import MenuItemCreateMessage, MenuItemResponse


@owner_controller.get("/menu-items")
@api.validate(
    resp=Response(
        HTTP_200=list[MenuItemResponse],
        HTTP_403=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def list_menu_items():
    # Lista o cardapio cadastrado pelo owner autenticado.
    # O MVP trabalha apenas com nome e preco de cada prato.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    items = (
        MenuItem.query.filter_by(owner_id=current_user.id)
        .order_by(MenuItem.name.asc(), MenuItem.id.asc())
        .all()
    )
    return [MenuItemResponse.model_validate(item, from_attributes=True).model_dump(mode="json") for item in items], 200


@owner_controller.post("/menu-items")
@api.validate(
    json=MenuItemCreateMessage,
    resp=Response(
        HTTP_201=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_403=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def create_menu_item():
    # Cadastra um prato simples no cardapio do owner.
    # Nao existe estrutura de categorias ou restaurante porque o objetivo aqui e um MVP funcional.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    name = data.name.strip()
    if not name:
        return {"msg": "name cannot be empty"}, 400

    item = MenuItem(
        owner_id=current_user.id,
        name=name,
        price=round(float(data.price), 2),
    )
    db.session.add(item)
    db.session.commit()

    return MenuItemResponse.model_validate(item, from_attributes=True).model_dump(mode="json"), 201


@owner_controller.put("/menu-items/<int:item_id>")
@api.validate(
    json=MenuItemCreateMessage,
    resp=Response(
        HTTP_200=MenuItemResponse,
        HTTP_400=SpectreeValidationError,
        HTTP_403=GenericResponse,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def update_menu_item(item_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    item = MenuItem.query.filter_by(id=item_id, owner_id=current_user.id).first()
    if not item:
        return {"msg": "Menu item not found"}, 404

    name = data.name.strip()
    if not name:
        return {"msg": "name cannot be empty"}, 400

    item.name = name
    item.price = round(float(data.price), 2)
    db.session.commit()

    return MenuItemResponse.model_validate(item, from_attributes=True).model_dump(mode="json"), 200


@owner_controller.delete("/menu-items/<int:item_id>")
@api.validate(
    resp=Response(
        HTTP_200=GenericResponse,
        HTTP_403=GenericResponse,
        HTTP_404=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def delete_menu_item(item_id):
    auth_error = owner_required()
    if auth_error:
        return auth_error

    item = MenuItem.query.filter_by(id=item_id, owner_id=current_user.id).first()
    if not item:
        return {"msg": "Menu item not found"}, 404

    db.session.delete(item)
    db.session.commit()
    return {"msg": "Menu item deleted"}, 200
