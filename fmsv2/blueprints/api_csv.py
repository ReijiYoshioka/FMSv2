from datetime import datetime

from flask import Blueprint, Response, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import csv_service
from ..services.errors import ValidationError
from ..utils.dates import is_valid_month_str
from ..utils.json_response import json_error, json_ok
from ..utils.numbers import lenient_int

bp = Blueprint("api_csv", __name__, url_prefix="/api/csv")


def _current_month():
    return datetime.now().strftime("%Y-%m")


@bp.route("", methods=["GET"])
@api_login_required
def export():
    month = request.args.get("month") or _current_month()
    if not is_valid_month_str(month):
        return json_error("monthの形式が不正です。")
    rows = csv_service.export_rows(
        get_db(),
        current_user_id(),
        month,
        q=request.args.get("q"),
        type_=request.args.get("type"),
        category_id=lenient_int(request.args.get("category_id")),
        min_amount=lenient_int(request.args.get("min")),
        max_amount=lenient_int(request.args.get("max")),
    )
    csv_text = csv_service.build_csv(rows)
    suffix = f"_{request.args.get('month')}" if request.args.get("month") else ""
    filename = f"fms_transactions{suffix}.csv"
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def import_():
    file = request.files.get("file")
    if file is None:
        return json_error("fileは必須です。")
    try:
        result = csv_service.import_csv(get_db(), current_user_id(), file)
    except ValidationError as e:
        return json_error(e.message, e.status)
    return json_ok(result)
