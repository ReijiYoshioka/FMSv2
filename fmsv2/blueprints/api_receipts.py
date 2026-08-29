from flask import Blueprint, current_app, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import receipt_service
from ..services.errors import ExternalServiceError, ValidationError
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_receipts", __name__, url_prefix="/api/receipts")


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def read():
    file = request.files.get("image")
    if file is None:
        return json_error("imageは必須です。")
    try:
        result = receipt_service.read_receipt(
            get_db(),
            current_user_id(),
            file,
            current_app.config["GEMINI_API_KEY"],
            current_app.config["GEMINI_MODEL"],
            current_app.config["RECEIPT_DAILY_LIMIT"],
        )
    except (ValidationError, ExternalServiceError) as e:
        return json_error(e.message, e.status)
    return json_ok(result)
