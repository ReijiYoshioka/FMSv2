from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..services import summary_repo
from ..utils.dates import is_valid_month_str, is_valid_year_str
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_summary", __name__, url_prefix="/api/summary")

_MONTH_MODES = {
    "monthly_stats": summary_repo.monthly_stats,
    "category_chart": summary_repo.category_chart,
    "payment_chart": summary_repo.payment_chart,
}
_YEAR_MODES = {
    "annual_stats": summary_repo.annual_stats,
    "annual_category_chart": summary_repo.annual_category_chart,
    "annual_payment_chart": summary_repo.annual_payment_chart,
    "annual_trend": summary_repo.annual_trend,
}


@bp.route("", methods=["GET"])
@api_login_required
def summary():
    mode = request.args.get("mode")
    db = get_db()
    user_id = current_user_id()

    if mode in _MONTH_MODES:
        month = request.args.get("month")
        if not month or not is_valid_month_str(month):
            return json_error("monthの形式が不正です。")
        return json_ok(_MONTH_MODES[mode](db, user_id, month))

    if mode in _YEAR_MODES:
        year = request.args.get("year")
        if not year or not is_valid_year_str(year):
            return json_error("yearの形式が不正です。")
        return json_ok(_YEAR_MODES[mode](db, user_id, year))

    return json_error("modeが不正です。")
