import hmac
from pathlib import Path

from flask import Blueprint, abort, current_app, request

from ..db import get_db
from ..utils.json_response import json_ok

bp = Blueprint("healthcheck", __name__)

REQUIRED_TABLES = [
    "users",
    "transactions",
    "transaction_items",
    "categories",
    "payment_methods",
    "login_attempts",
]


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
    for table in REQUIRED_TABLES:
        try:
            count = db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
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
