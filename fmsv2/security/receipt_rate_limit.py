def record_attempt(db, user_id):
    db.execute("INSERT INTO receipt_read_attempts (user_id) VALUES (?)", (user_id,))
    db.commit()


def is_allowed(db, user_id, limit):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM receipt_read_attempts "
        "WHERE user_id = ? AND attempted_at >= datetime('now', 'localtime', '-24 hours')",
        (user_id,),
    ).fetchone()
    return row["n"] < limit
