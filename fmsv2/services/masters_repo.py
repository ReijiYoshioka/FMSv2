import sqlite3

from .errors import ConflictError, ValidationError

VALID_KINDS = {"category": "categories", "payment": "payment_methods"}


def list_masters(db):
    categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY id").fetchall()]
    payment_rows = db.execute("SELECT * FROM payment_methods ORDER BY id").fetchall()
    return {"categories": categories, "payment_methods": [dict(r) for r in payment_rows]}


def _table_for(kind):
    table = VALID_KINDS.get(kind)
    if table is None:
        raise ValidationError("kindはcategoryまたはpaymentで指定してください。")
    return table


def _to_valid_id(value):
    """0・None・数値以外は「未指定」として扱う（idは1始まりのAUTOINCREMENTのため）。"""
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return None
    return int_value if int_value > 0 else None


def add_or_rename(db, kind, name, master_id=None):
    table = _table_for(kind)
    name = str(name).strip()
    if not (1 <= len(name) <= 50):
        raise ValidationError("名前は1〜50文字で指定してください。")

    master_id = _to_valid_id(master_id)
    try:
        if master_id is not None:
            cursor = db.execute(f"UPDATE {table} SET name = ? WHERE id = ?", (name, master_id))
            db.commit()
            if cursor.rowcount == 0:
                raise ValidationError("見つかりません。", 404)
            return master_id
        cursor = db.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ConflictError("既に存在します。") from None


def is_in_use(db, kind, master_id):
    if kind == "category":
        tables_columns = [
            ("transactions", "category_id"),
            ("transaction_items", "category_id"),
            ("recurring_transactions", "category_id"),
            ("budgets", "category_id"),
        ]
    else:
        tables_columns = [
            ("transactions", "payment_method_id"),
            ("recurring_transactions", "payment_method_id"),
        ]
    for table, column in tables_columns:
        count = db.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (master_id,)
        ).fetchone()["n"]
        if count > 0:
            return True
    return False


def delete(db, kind, master_id):
    table = _table_for(kind)
    master_id = _to_valid_id(master_id)
    if master_id is None:
        raise ValidationError("idは必須です。")
    if is_in_use(db, kind, master_id):
        raise ConflictError("使用中のため削除できません。")
    cursor = db.execute(f"DELETE FROM {table} WHERE id = ?", (master_id,))
    db.commit()
    return cursor.rowcount > 0
