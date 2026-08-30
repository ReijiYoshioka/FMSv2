from flask import Blueprint, current_app, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..services import places_service
from ..services.errors import ExternalServiceError, ValidationError
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_places", __name__, url_prefix="/api/places")


@bp.route("/suggest", methods=["GET"])
@api_login_required
def suggest():
    try:
        results = places_service.suggest(
            get_db(),
            current_user_id(),
            request.args.get("q", ""),
            request.args.get("lat"),
            request.args.get("lng"),
            current_app.config["GEMINI_API_KEY"],
            current_app.config["GEMINI_MODEL"],
            current_app.config["PLACE_SUGGEST_DAILY_LIMIT"],
        )
    except (ValidationError, ExternalServiceError) as e:
        return json_error(e.message, e.status)
    return json_ok({"suggestions": results})
