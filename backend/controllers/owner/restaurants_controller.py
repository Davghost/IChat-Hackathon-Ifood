from factory import api, db
from flask import request
from flask_jwt_extended import current_user, jwt_required
from models.restaurant import Restaurant
from spectree import Response

from utils.response_schema import GenericResponse
from .access import get_owner_restaurant, owner_required
from .blueprint import owner_controller
from .schemas import RestaurantMessage, RestaurantResponse
from .serializers import restaurant_response

@owner_controller.post("/restaurant")
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_201=RestaurantResponse, HTTP_400=GenericResponse),
    tags=["owner"],
)
@jwt_required()
def create_restaurant():
    # Esta rota cria o restaurante do dono autenticado.
    # Primeiro garantimos que o JWT pertence a um usuario com papel de owner.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    # Cada owner pode manter apenas um restaurante no modelo atual.
    # Se um registro ja existir, a criacao e bloqueada para evitar duplicidade.
    if get_owner_restaurant():
        return {"msg": "Owner already has a restaurant"}, 400

    # O payload validado pelo Spectree/Pydantic fica em request.context.json.
    # Isso evita ler campos crus sem validacao de tipo e presenca.
    data = request.context.json
    restaurant = Restaurant(
        name=data.name,
        description=data.description,
        owner=current_user._get_current_object(),
    )

    # Persistimos o novo restaurante e devolvemos o shape publico padronizado.
    db.session.add(restaurant)
    db.session.commit()

    return restaurant_response(restaurant), 201


@owner_controller.get("/restaurant")
@api.validate(resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def get_restaurant():
    # A consulta do restaurante do owner sempre usa o usuario autenticado como filtro.
    # Isso impede acesso a restaurantes de outros donos.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    # A resposta passa pelo serializer para manter consistencia entre endpoints.
    return restaurant_response(restaurant), 200


@owner_controller.put("/restaurant")
@api.validate(
    json=RestaurantMessage,
    resp=Response(HTTP_200=RestaurantResponse, HTTP_404=GenericResponse),
    tags=["owner"],
)
@jwt_required()
def update_restaurant():
    # A atualizacao reutiliza o mesmo contrato de entrada da criacao:
    # nome e descricao completos do restaurante.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    # Como o restaurante ja existe, sobrescrevemos os campos e confirmamos a transacao.
    data = request.context.json
    restaurant.name = data.name
    restaurant.description = data.description
    db.session.commit()

    return restaurant_response(restaurant), 200


@owner_controller.delete("/restaurant")
@api.validate(resp=Response(HTTP_200=GenericResponse, HTTP_404=GenericResponse), tags=["owner"])
@jwt_required()
def delete_restaurant():
    # A exclusao e restrita ao restaurante pertencente ao owner autenticado.
    # Nao ha lookup por id na URL justamente para reduzir superficie de acesso indevido.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    restaurant = get_owner_restaurant()
    if not restaurant:
        return {"msg": "Restaurant not found"}, 404

    # Removemos o registro e retornamos uma mensagem simples de sucesso.
    db.session.delete(restaurant)
    db.session.commit()

    return {"msg": "Restaurant deleted successfully"}, 200
