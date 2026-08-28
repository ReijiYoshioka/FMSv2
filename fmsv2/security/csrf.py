import hmac
import secrets
from functools import wraps

from flask import jsonify, request, session


def csrf_token():
    """セッションのCSRFトークンを取得する。無ければ生成する。"""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def verify_csrf(token):
    """タイミング安全にCSRFトークンを検証する。"""
    session_token = session.get("csrf_token")
    if not session_token or not isinstance(token, str):
        return False
    return hmac.compare_digest(session_token, token)


def _extract_token():
    header_token = request.headers.get("X-CSRF-Token")
    if header_token:
        return header_token
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        return body.get("csrf_token")
    return request.form.get("csrf_token")


def require_csrf(f):
    """POST/DELETEハンドラの先頭で呼ぶCSRF検証デコレータ（API向け）。"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not verify_csrf(_extract_token()):
            message = "CSRFトークンが不正です。ページを再読み込みしてください。"
            response = jsonify({"error": message})
            response.status_code = 403
            return response
        return f(*args, **kwargs)

    return wrapper
