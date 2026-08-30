from flask import Blueprint, current_app, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import chat_service
from ..services.errors import ExternalServiceError, ValidationError
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_chat", __name__, url_prefix="/api/chat")


@bp.route("/parse", methods=["POST"])
@api_login_required
@require_csrf
def parse():
    payload = request.get_json(silent=True) or {}
    try:
        result = chat_service.parse(
            get_db(),
            current_user_id(),
            payload.get("messages"),
            current_app.config["GEMINI_API_KEY"],
            current_app.config["GEMINI_MODEL"],
            current_app.config["CHAT_DAILY_LIMIT"],
        )
    except (ValidationError, ExternalServiceError) as e:
        return json_error(e.message, e.status)
    return json_ok(result)
