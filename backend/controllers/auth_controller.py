from factory import api, db
from sqlalchemy import select
from pydantic import BaseModel
from spectree import Response

from flask import Blueprint, request
from flask_jwt_extended import create_access_token

from models import User
from utils.response_schema import GenericResponse

auth_controller = Blueprint("auth_controller", __name__, url_prefix="/api/auth")


class LoginMessage(BaseModel):
    email: str
    password: str


class LoginResponseMessage(BaseModel):
    access_token: str


@auth_controller.post("/login")
@api.validate(
    json=LoginMessage,
    resp=Response(HTTP_200=LoginResponseMessage, HTTP_401=GenericResponse),
    tags=["auth"],
    security={},
)
def login():
    # Esta rota autentica apenas usuarios owner.
    # O payload ja foi validado por Pydantic, entao ambos os campos existem e tem tipo string.
    data = request.json

    # Buscamos o owner pelo email informado.
    # Se o email existir para outro papel, ele nao deve receber token nesta aplicacao.
    user = db.session.scalars(select(User).filter_by(email=data["email"])).first()

    # verify_password encapsula a comparacao segura do hash da senha.
    # A emissao do token exige credenciais validas e papel owner.
    if user and user.role == "owner" and user.verify_password(data["password"]):
        return {
            "access_token": create_access_token(identity=user.email, expires_delta=None)
        }

    # A resposta de erro nao distingue papel invalido, email inexistente ou senha incorreta.
    # Isso evita vazar informacao sobre quais contas existem na base.
    return {"msg": "Owner email and password do not match."}, 401
