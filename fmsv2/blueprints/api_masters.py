from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required
from ..security.csrf import require_csrf
from ..services import masters_repo
from ..services.errors import ConflictError, NotFoundError, ValidationError
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_masters", __name__, url_prefix="/api/masters")


@bp.route("", methods=["GET"])
@api_login_required
def list_masters():
    return json_ok(masters_repo.list_masters(get_db()))


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def add_or_rename():
    payload = request.get_json(silent=True) or {}
    try:
        new_id = masters_repo.add_or_rename(
            get_db(), payload.get("kind"), payload.get("name", ""), payload.get("id")
        )
    except ValidationError as e:
        return json_error(e.message, e.status)
    except ConflictError as e:
        return json_error(e.message, 409)
    except NotFoundError:
        return json_error("見つかりません。", 404)
    return json_ok({"id": new_id})


@bp.route("", methods=["DELETE"])
@api_login_required
@require_csrf
def delete():
    payload = request.get_json(silent=True) or {}
    try:
        deleted = masters_repo.delete(get_db(), payload.get("kind"), payload.get("id"))
    except ValidationError as e:
        return json_error(e.message, e.status)
    except ConflictError as e:
        return json_error(e.message, 409)
    if not deleted:
        return json_error("見つかりません。", 404)
    return json_ok({"deleted": True})
