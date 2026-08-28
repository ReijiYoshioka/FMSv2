from flask import Blueprint, request

from ..db import get_db
from ..security.auth import api_login_required, current_user_id
from ..security.csrf import require_csrf
from ..services import users_repo
from ..utils.json_response import json_error, json_ok

bp = Blueprint("api_account", __name__, url_prefix="/api/account")


@bp.route("", methods=["POST"])
@api_login_required
@require_csrf
def change_password():
    payload = request.get_json(silent=True) or {}
    current_password = payload.get("current_password", "")
    new_password = payload.get("new_password", "")

    if len(new_password) < users_repo.MIN_PASSWORD_LEN:
        message = f"新しいパスワードは{users_repo.MIN_PASSWORD_LEN}文字以上で指定してください。"
        return json_error(message)
    if new_password == current_password:
        return json_error("新しいパスワードは現在のパスワードと異なるものにしてください。")

    db = get_db()
    user = users_repo.find_by_id(db, current_user_id())
    if not users_repo.verify_password(user, current_password):
        return json_error("現在のパスワードが正しくありません。", 403)

    users_repo.update_password(db, user["id"], new_password)
    return json_ok({"changed": True})
