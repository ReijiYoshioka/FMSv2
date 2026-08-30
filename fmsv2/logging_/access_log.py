import logging
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import current_app, g, request, session

RETENTION_DAYS = 365
_logger = logging.getLogger(__name__)


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _client_ip():
    """信頼できるリバースプロキシ経由の場合はProxyFix（__init__.py）が
    request.remote_addrを書き換える。設定が無い限りX-Forwarded-Forは
    クライアントが自由に偽装できるため直接は信用しない。"""
    return request.remote_addr or ""


def _log_path():
    return Path(current_app.config["ACCESS_LOG_PATH"])


def _append_line(line):
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _before_request():
    g.access_log_token = secrets.token_hex(4)
    g.access_log_start = time.monotonic()
    try:
        user = session.get("username", "-")
        _append_line(
            f"{_now_str()} BEGIN method={request.method} path={request.full_path} "
            f"user={user} ip={_client_ip()} token={g.access_log_token}"
        )
    except OSError:
        _logger.warning("access log write failed", exc_info=True)


def _after_request(response):
    token = g.pop("access_log_token", None)
    if token is not None:
        try:
            start = g.pop("access_log_start", time.monotonic())
            elapsed_ms = int((time.monotonic() - start) * 1000)
            _append_line(
                f"{_now_str()} END status={response.status_code} "
                f"elapsed_ms={elapsed_ms} token={token}"
            )
            _maybe_prune()
        except OSError:
            _logger.warning("access log write/prune failed", exc_info=True)
    return response


def _prune_state_path():
    return _log_path().with_suffix(".prune_state")


def _maybe_prune():
    state_path = _prune_state_path()
    today = datetime.now().strftime("%Y-%m-%d")
    if state_path.exists() and state_path.read_text(encoding="utf-8").strip() == today:
        return
    prune_old_entries()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(today, encoding="utf-8")


def prune_old_entries():
    """RETENTION_DAYSより古い行を削除する（一時ファイル→renameで原子的に置換）。"""
    path = _log_path()
    if not path.exists():
        return
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    kept_lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                kept_lines.append(line)
                continue
            if ts >= cutoff:
                kept_lines.append(line)

    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.writelines(kept_lines)
    tmp_path.replace(path)


def init_app(app):
    app.before_request(_before_request)
    app.after_request(_after_request)
