from flask import Blueprint, redirect, render_template, request, session, url_for

from ..db import get_db
from ..security.auth import current_user_id
from ..security.csrf import csrf_token, verify_csrf
from ..security.rate_limit import (
    client_ip,
    is_locked_out,
    is_register_locked_out,
    record_attempt,
    record_register_attempt,
)
from ..services import users_repo

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user_id() is not None:
        return redirect(url_for("pages.monthly"))
    error = None
    if request.method == "POST":
        if not verify_csrf(request.form.get("csrf_token")):
            error = "CSRFトークンが不正です。ページを再読み込みしてください。"
        else:
            db = get_db()
            ip = client_ip(request)
            if is_locked_out(db, ip):
                error = "ログイン試行回数が上限を超えました。15分後に再試行してください。"
            else:
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                user = users_repo.find_by_username(db, username)
                ok = user is not None and users_repo.verify_password(user, password)
                record_attempt(db, ip, username, ok)
                if ok:
                    session.clear()
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    return redirect(url_for("pages.monthly"))
                error = "ユーザー名またはパスワードが間違っています。"
    return render_template("auth/login.html", error=error, csrf_token=csrf_token())


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user_id() is not None:
        return redirect(url_for("pages.monthly"))
    error = None
    success = False
    if request.method == "POST":
        if not verify_csrf(request.form.get("csrf_token")):
            error = "CSRFトークンが不正です。ページを再読み込みしてください。"
        else:
            db = get_db()
            ip = client_ip(request)
            if is_register_locked_out(db, ip):
                error = "登録試行回数が上限を超えました。しばらくしてから再試行してください。"
            else:
                record_register_attempt(db, ip)
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "")
                if len(username) < users_repo.MIN_USERNAME_LEN:
                    error = f"ユーザー名は{users_repo.MIN_USERNAME_LEN}文字以上で入力してください。"
                elif len(password) < users_repo.MIN_PASSWORD_LEN:
                    error = f"パスワードは{users_repo.MIN_PASSWORD_LEN}文字以上で入力してください。"
                else:
                    try:
                        users_repo.create_user(db, username, password)
                        success = True
                    except users_repo.UsernameTakenError:
                        error = "そのユーザー名は既に使われています。"
    return render_template(
        "auth/register.html", error=error, success=success, csrf_token=csrf_token()
    )


@bp.route("/logout", methods=["POST"])
def logout():
    if not verify_csrf(request.form.get("csrf_token")):
        return "CSRFトークンが不正です。", 403
    session.clear()
    return redirect(url_for("auth.login"))
