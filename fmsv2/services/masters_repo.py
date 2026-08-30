import sqlite3

from .errors import ConflictError, NotFoundError, ValidationError

VALID_KINDS = ("category", "payment")


def list_masters(db):
    categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY id").fetchall()]
    payment_rows = db.execute("SELECT * FROM payment_methods ORDER BY id").fetchall()
    return {"categories": categories, "payment_methods": [dict(r) for r in payment_rows]}


def _validate_kind(kind):
    if kind not in VALID_KINDS:
        raise ValidationError("kindはcategoryまたはpaymentで指定してください。")


def _to_valid_id(value):
    """0・None・数値以外は「未指定」として扱う（idは1始まりのAUTOINCREMENTのため）。"""
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return None
    return int_value if int_value > 0 else None


def _insert(db, kind, name):
    if kind == "category":
        return db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    return db.execute("INSERT INTO payment_methods (name) VALUES (?)", (name,))


def _update_name(db, kind, master_id, name):
    if kind == "category":
        return db.execute("UPDATE categories SET name = ? WHERE id = ?", (name, master_id))
    return db.execute("UPDATE payment_methods SET name = ? WHERE id = ?", (name, master_id))


def _delete_row(db, kind, master_id):
    if kind == "category":
        return db.execute("DELETE FROM categories WHERE id = ?", (master_id,))
    return db.execute("DELETE FROM payment_methods WHERE id = ?", (master_id,))


def add_or_rename(db, kind, name, master_id=None):
    _validate_kind(kind)
    name = str(name).strip()
    if not (1 <= len(name) <= 50):
        raise ValidationError("名前は1〜50文字で指定してください。")

    master_id = _to_valid_id(master_id)
    try:
        if master_id is not None:
            cursor = _update_name(db, kind, master_id, name)
            db.commit()
            if cursor.rowcount == 0:
                raise NotFoundError()
            return master_id
        cursor = _insert(db, kind, name)
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ConflictError("既に存在します。") from None


def is_in_use(db, kind, master_id):
    if kind == "category":
        counts = [
            db.execute(
                "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?", (master_id,)
            ).fetchone()["n"],
            db.execute(
                "SELECT COUNT(*) AS n FROM transaction_items WHERE category_id = ?", (master_id,)
            ).fetchone()["n"],
            db.execute(
                "SELECT COUNT(*) AS n FROM recurring_transactions WHERE category_id = ?",
                (master_id,),
            ).fetchone()["n"],
            db.execute(
                "SELECT COUNT(*) AS n FROM budgets WHERE category_id = ?", (master_id,)
            ).fetchone()["n"],
        ]
    else:
        counts = [
            db.execute(
                "SELECT COUNT(*) AS n FROM transactions WHERE payment_method_id = ?", (master_id,)
            ).fetchone()["n"],
            db.execute(
                "SELECT COUNT(*) AS n FROM recurring_transactions WHERE payment_method_id = ?",
                (master_id,),
            ).fetchone()["n"],
        ]
    return any(c > 0 for c in counts)


def delete(db, kind, master_id):
    _validate_kind(kind)
    master_id = _to_valid_id(master_id)
    if master_id is None:
        raise ValidationError("idは必須です。")
    if is_in_use(db, kind, master_id):
        raise ConflictError("使用中のため削除できません。")
    cursor = _delete_row(db, kind, master_id)
    db.commit()
    return cursor.rowcount > 0
