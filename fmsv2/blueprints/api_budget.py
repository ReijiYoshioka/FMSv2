from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import budget_repo
from ..services.errors import ValidationError
from ..utils.dates import is_valid_month_str
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_budget", __name__, url_prefix="/api/budget")


@bp.route("", methods=["GET"])
@api_login_required
def get_status():
    month = request.args.get("month")
    if not month or not is_valid_month_str(month):
        return json_error("monthの形式が不正です。")
    return json_ok(budget_repo.get_budget_status(get_db(), current_user_id(), month))


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def save():
    payload = request.get_json(silent=True) or {}
    db = get_db()
    user_id = current_user_id()

    if request.args.get("action") == "copy_prev" or payload.get("action") == "copy_prev":
        month = payload.get("month")
        if not month or not is_valid_month_str(month):
            return json_error("monthの形式が不正です。")
        count = budget_repo.copy_prev_month(db, user_id, month)
        return json_ok({"copied": count})

    month = payload.get("month")
    if not month or not is_valid_month_str(month):
        return json_error("monthの形式が不正です。")

    if "items" in payload:
        saved = budget_repo.save_items(db, user_id, month, payload["items"])
        return json_ok({"saved": saved})

    category_id = payload.get("category_id")
    amount = payload.get("amount")
    if category_id is None or amount is None:
        return json_error("category_idとamountは必須です。")
    try:
        budget_repo.save_single(db, user_id, month, category_id, amount)
    except ValidationError as e:
        return json_error(e.message, e.status)
    return json_ok({"saved": 1})


@bp.route("", methods=["DELETE"])
@api_login_required
@require_csrf
def delete():
    payload = request.get_json(silent=True) or {}
    month = payload.get("month")
    category_id = payload.get("category_id")
    if not month or not is_valid_month_str(month) or category_id is None:
        return json_error("monthとcategory_idは必須です。")
    deleted = budget_repo.delete_budget(get_db(), current_user_id(), month, category_id)
    if not deleted:
        return json_error("予算が見つかりません。", 404)
    return json_ok({"deleted": True})
