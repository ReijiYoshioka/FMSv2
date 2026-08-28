from datetime import datetime

from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import transactions_repo
from ..services.errors import NotFoundError, ValidationError
from ..utils.dates import is_valid_month_str
from ..utils.json_response import json_error, json_ok
from ..utils.numbers import lenient_int

bp = Blueprint("api_transactions", __name__, url_prefix="/api/transactions")


def _current_month():
    return datetime.now().strftime("%Y-%m")


@bp.route("", methods=["GET"])
@api_login_required
def list_or_metadata():
    db = get_db()
    if request.args.get("action") == "metadata":
        category_rows = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
        payment_rows = db.execute("SELECT * FROM payment_methods ORDER BY id").fetchall()
        categories = [dict(r) for r in category_rows]
        payment_methods = [dict(r) for r in payment_rows]
        return json_ok({"categories": categories, "payment_methods": payment_methods})

    month = request.args.get("month") or _current_month()
    if not is_valid_month_str(month):
        return json_error("monthの形式が不正です。")

    min_amount = lenient_int(request.args.get("min"))
    max_amount = lenient_int(request.args.get("max"))
    category_id = lenient_int(request.args.get("category_id"))

    items = transactions_repo.list_transactions(
        db,
        current_user_id(),
        month,
        q=request.args.get("q"),
        type_=request.args.get("type"),
        category_id=category_id,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    return json_ok({"transactions": items})


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def create_or_update():
    payload = request.get_json(silent=True) or {}
    tx_id = payload.get("id")
    try:
        new_id = transactions_repo.create_or_update(get_db(), current_user_id(), payload, tx_id)
    except ValidationError as e:
        return json_error(e.message, e.status)
    except NotFoundError:
        return json_error("取引が見つかりません。", 404)
    return json_ok({"id": new_id})


@bp.route("/<int:tx_id>", methods=["DELETE"])
@api_login_required
@require_csrf
def delete(tx_id):
    deleted = transactions_repo.delete_transaction(get_db(), current_user_id(), tx_id)
    if not deleted:
        return json_error("取引が見つかりません。", 404)
    return json_ok({"deleted": True})
