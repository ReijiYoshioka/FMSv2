LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MIN = 15
REGISTER_MAX_ATTEMPTS = 5
REGISTER_WINDOW_MIN = 60


def is_locked_out(db, ip_address):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM login_attempts "
        "WHERE ip_address = ? AND success = 0 "
        "AND attempted_at >= datetime('now', 'localtime', ?)",
        (ip_address, f"-{LOGIN_WINDOW_MIN} minutes"),
    ).fetchone()
    return row["n"] >= LOGIN_MAX_ATTEMPTS


def record_attempt(db, ip_address, username, success):
    db.execute(
        "INSERT INTO login_attempts (ip_address, username, success) VALUES (?, ?, ?)",
        (ip_address, username, 1 if success else 0),
    )
    db.commit()


def is_register_locked_out(db, ip_address):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM register_attempts "
        "WHERE ip_address = ? AND attempted_at >= datetime('now', 'localtime', ?)",
        (ip_address, f"-{REGISTER_WINDOW_MIN} minutes"),
    ).fetchone()
    return row["n"] >= REGISTER_MAX_ATTEMPTS


def record_register_attempt(db, ip_address):
    db.execute("INSERT INTO register_attempts (ip_address) VALUES (?)", (ip_address,))
    db.commit()


def client_ip(request):
    """信頼できるリバースプロキシ経由の場合はProxyFix（__init__.py）が
    request.remote_addrを書き換える。設定が無い限りX-Forwarded-Forは
    クライアントが自由に偽装できるため直接は信用しない。"""
    return request.remote_addr or ""
