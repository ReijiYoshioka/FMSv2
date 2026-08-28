import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

MIN_USERNAME_LEN = 3
MIN_PASSWORD_LEN = 8


class UsernameTakenError(Exception):
    pass


def find_by_username(db, username):
    return db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def find_by_id(db, user_id):
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(db, username, password):
    password_hash = generate_password_hash(password)
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise UsernameTakenError() from e
    return cursor.lastrowid


def verify_password(user_row, password):
    return check_password_hash(user_row["password_hash"], password)


def update_password(db, user_id, new_password):
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    db.commit()
