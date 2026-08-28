from functools import wraps

from flask import jsonify, redirect, session, url_for


def current_user_id():
    return session.get("user_id")


def login_required(f):
    """画面ルート用。未認証は/loginへリダイレクトする。"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user_id() is None:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapper


def api_login_required(f):
    """APIルート用。未認証は401 JSONを返す。"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user_id() is None:
            response = jsonify({"error": "認証が必要です。"})
            response.status_code = 401
            return response
        return f(*args, **kwargs)

    return wrapper
