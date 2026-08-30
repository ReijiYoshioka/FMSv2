import hmac
from pathlib import Path

from flask import Blueprint, abort, current_app, request

from ..db import get_db
from ..utils.json_response import json_ok

bp = Blueprint("healthcheck", __name__)

# テーブル名をf-stringでSQLに埋め込まず、クエリ全体を固定文字列として持つ
# （「SQLは必ずパラメータ化/リテラルで書く」方針を徹底するため）。
REQUIRED_TABLE_QUERIES = {
    "users": "SELECT COUNT(*) AS n FROM users",
    "transactions": "SELECT COUNT(*) AS n FROM transactions",
    "transaction_items": "SELECT COUNT(*) AS n FROM transaction_items",
    "categories": "SELECT COUNT(*) AS n FROM categories",
    "payment_methods": "SELECT COUNT(*) AS n FROM payment_methods",
    "login_attempts": "SELECT COUNT(*) AS n FROM login_attempts",
}


def _check_log_writable():
    try:
        log_path = Path(current_app.config["ACCESS_LOG_PATH"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        probe = log_path.parent / ".healthcheck_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


@bp.route("/healthcheck")
def healthcheck():
    expected = current_app.config.get("HEALTHCHECK_TOKEN", "")
    token = request.args.get("token", "")
    if not expected or not hmac.compare_digest(expected, token):
        abort(404)

    db = get_db()
    tables = {}
    for table, query in REQUIRED_TABLE_QUERIES.items():
        try:
            count = db.execute(query).fetchone()["n"]
            tables[table] = {"exists": True, "count": count}
        except Exception:
            tables[table] = {"exists": False, "count": None}

    return json_ok(
        {
            "database": "ok",
            "tables": tables,
            "logs_writable": _check_log_writable(),
        }
    )
