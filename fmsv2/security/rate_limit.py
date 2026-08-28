LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MIN = 15


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


def client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""
