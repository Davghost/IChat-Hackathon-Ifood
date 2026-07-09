from email.mime import message
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, request
from flask_jwt_extended import current_user, jwt_required
from pydantic import BaseModel
from spectree import Response

from factory import api
from utils.response_schema import GenericResponse
from .owner.access import owner_required


CHATBOT_WEBHOOK_URL = "https://gflaulhabe132.app.n8n.cloud/webhook/Hackathon-iFood/chat"
chat_controller = Blueprint("chat_controller", __name__, url_prefix="/api/owner")


class ChatMessageRequest(BaseModel):
    message: str


class ChatForwardPayloadResponse(BaseModel):
    client_id: int
    restaurant_id: int
    message: str


class ChatMessageResponse(BaseModel):
    forwarded_payload: ChatForwardPayloadResponse
    chatbot_response: dict | list | str | None


@chat_controller.post("/chat")
@api.validate(
    json=ChatMessageRequest,
    resp=Response(
        HTTP_200=ChatMessageResponse,
        HTTP_400=GenericResponse,
        HTTP_403=GenericResponse,
        HTTP_502=GenericResponse,
    ),
    tags=["owner"],
)
@jwt_required()
def send_chat_message():
    # Esta rota existe para o owner enviar uma mensagem ao chatbot externo.
    # O frontend informa apenas a mensagem; os demais campos obrigatorios do webhook
    # sao preenchidos pelo backend para manter o contrato consistente.
    auth_error = owner_required()
    if auth_error:
        return auth_error

    data = request.context.json
    message = data.message.strip()
    if not message:
        return {"msg": "message cannot be empty"}, 400

    # client_id sempre representa o id do owner autenticado.
    # restaurant_id e fixado como 1 por exigencia do contrato atual,
    # mesmo que nao exista uma tabela ou registro real de restaurante.
    payload = {
        "client_id": current_user.id,
        "restaurant_id": 1,
        "message": message,
    }

    encoded_payload = json.dumps(payload).encode("utf-8")
    webhook_request = Request(
        CHATBOT_WEBHOOK_URL,
        data=encoded_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(webhook_request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return {"msg": f"Chatbot webhook returned HTTP {exc.code}: {error_body}"}, 502
    except URLError as exc:
        return {"msg": f"Could not reach chatbot webhook: {exc.reason}"}, 502

    try:
        chatbot_response = json.loads(response_body) if response_body else None
    except json.JSONDecodeError:
        chatbot_response = response_body or None

    response = ChatMessageResponse(
        forwarded_payload=ChatForwardPayloadResponse(**payload),
        chatbot_response=chatbot_response,
    )
    return response.model_dump(mode="json"), 200
