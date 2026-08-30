def record_attempt(db, user_id, endpoint):
    db.execute(
        "INSERT INTO api_call_attempts (user_id, endpoint) VALUES (?, ?)", (user_id, endpoint)
    )
    db.commit()


def is_allowed(db, user_id, endpoint, limit):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM api_call_attempts "
        "WHERE user_id = ? AND endpoint = ? "
        "AND attempted_at >= datetime('now', 'localtime', '-24 hours')",
        (user_id, endpoint),
    ).fetchone()
    return row["n"] < limit
