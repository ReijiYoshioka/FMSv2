from datetime import datetime

from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import recurring_repo
from ..services.errors import NotFoundError, ValidationError
from ..utils.dates import is_valid_month_str
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_recurring", __name__, url_prefix="/api/recurring")


def _current_month():
    return datetime.now().strftime("%Y-%m")


@bp.route("", methods=["GET"])
@api_login_required
def list_recurring():
    month = request.args.get("month") or _current_month()
    if not is_valid_month_str(month):
        return json_error("monthの形式が不正です。")
    items = recurring_repo.list_recurring(get_db(), current_user_id(), month)
    return json_ok({"recurring": items})


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def create_or_update():
    payload = request.get_json(silent=True) or {}

    if payload.get("action") == "apply" or request.args.get("action") == "apply":
        month = payload.get("month") or _current_month()
        if not is_valid_month_str(month):
            return json_error("monthの形式が不正です。")
        result = recurring_repo.apply_all(get_db(), current_user_id(), month)
        return json_ok(result)

    recurring_id = payload.get("id")
    try:
        new_id = recurring_repo.create_or_update(get_db(), current_user_id(), payload, recurring_id)
    except ValidationError as e:
        return json_error(e.message, e.status)
    except NotFoundError:
        return json_error("定期取引が見つかりません。", 404)
    return json_ok({"id": new_id})


@bp.route("/<int:recurring_id>", methods=["DELETE"])
@api_login_required
@require_csrf
def delete(recurring_id):
    deleted = recurring_repo.delete_recurring(get_db(), current_user_id(), recurring_id)
    if not deleted:
        return json_error("定期取引が見つかりません。", 404)
    return json_ok({"deleted": True})
