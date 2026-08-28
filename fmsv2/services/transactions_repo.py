import math
from datetime import datetime

from ..utils.dates import month_range
from .errors import NotFoundError, ValidationError

VALID_TYPES = ("income", "expense")


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _is_numeric(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, str):
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False
    return False


def _coerce_id_lenient(value):
    """category_id/payment_method_id等。数値でなければ黙ってNoneにフォールバックする
    （旧版の`is_numeric($v) ? (int)$v : null`と同じ方針）。"""
    if not _is_numeric(value):
        return None
    return int(float(value))


def _coerce_id_strict(value, message):
    """内訳のcategory_idのように、指定されているのに数値でなければ400にする。"""
    if value is None:
        return None
    if not _is_numeric(value):
        raise ValidationError(message)
    return int(float(value))


def _coerce_amount(value, message):
    if not _is_numeric(value):
        raise ValidationError(message)
    amount = int(float(value))
    if amount < 0:
        raise ValidationError(message)
    return amount


def parse_date(date_str):
    if date_str is None:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not isinstance(date_str, str):
        raise ValidationError("dateの形式が不正です。")

    normalized = date_str.strip().replace("T", " ")
    if not normalized:
        raise ValidationError("dateの形式が不正です。")

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ValidationError("dateの形式が不正です。") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _most_frequent_category_id(items):
    counts = {}
    order = []
    for item in items:
        cid = item.get("category_id")
        if cid is None:
            continue
        if cid not in counts:
            counts[cid] = 0
            order.append(cid)
        counts[cid] += 1
    if not counts:
        return None
    best = order[0]
    for cid in order:
        if counts[cid] > counts[best]:
            best = cid
    return best


def _validate_items(raw_items):
    if not isinstance(raw_items, list):
        return []
    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValidationError("内訳の形式が不正です。")
        item_name = str(raw.get("item_name", "")).strip()
        if not item_name:
            raise ValidationError("内訳の品名は必須です。")
        amount = _coerce_amount(raw.get("amount"), "内訳の金額は0以上の数値で指定してください。")
        category_id = _coerce_id_strict(raw.get("category_id"), "内訳のカテゴリーが不正です。")
        items.append({"item_name": item_name, "amount": amount, "category_id": category_id})
    return items


def _attach_items(db, transactions):
    if not transactions:
        return []
    ids = [t["id"] for t in transactions]
    placeholders = ",".join("?" for _ in ids)
    rows = db.execute(
        "SELECT ti.*, c.name AS category_name FROM transaction_items ti "
        "LEFT JOIN categories c ON c.id = ti.category_id "
        f"WHERE ti.transaction_id IN ({placeholders})",
        ids,
    ).fetchall()
    items_by_tx = {}
    for row in rows:
        items_by_tx.setdefault(row["transaction_id"], []).append(dict(row))
    result = []
    for t in transactions:
        entry = dict(t)
        entry["items"] = items_by_tx.get(t["id"], [])
        result.append(entry)
    return result


def list_transactions(
    db, user_id, month, q=None, type_=None, category_id=None, min_amount=None, max_amount=None
):
    start, end = month_range(month)
    conditions = ["user_id = ?", "date >= ?", "date < ?"]
    params = [user_id, start, end]

    q = (q or "").strip()
    if q:
        escaped = _escape_like(q)
        conditions.append("(description LIKE ? ESCAPE '\\' OR memo LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    if type_ in VALID_TYPES:
        conditions.append("type = ?")
        params.append(type_)
    if category_id is not None:
        conditions.append("category_id = ?")
        params.append(category_id)
    if min_amount is not None:
        conditions.append("amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        conditions.append("amount <= ?")
        params.append(max_amount)

    sql = (
        "SELECT t.*, c.name AS category_name, p.name AS payment_method_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON c.id = t.category_id "
        "LEFT JOIN payment_methods p ON p.id = t.payment_method_id "
        "WHERE " + " AND ".join(conditions) + " ORDER BY t.date DESC, t.id DESC"
    )
    rows = db.execute(sql, params).fetchall()
    return _attach_items(db, rows)


def get_transaction(db, user_id, tx_id):
    row = db.execute(
        "SELECT t.*, c.name AS category_name, p.name AS payment_method_name "
        "FROM transactions t "
        "LEFT JOIN categories c ON c.id = t.category_id "
        "LEFT JOIN payment_methods p ON p.id = t.payment_method_id "
        "WHERE t.id = ? AND t.user_id = ?",
        (tx_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _attach_items(db, [row])[0]


def _save_items(db, tx_id, items):
    db.execute("DELETE FROM transaction_items WHERE transaction_id = ?", (tx_id,))
    for item in items:
        db.execute(
            "INSERT INTO transaction_items (transaction_id, item_name, amount, category_id) "
            "VALUES (?, ?, ?, ?)",
            (tx_id, item["item_name"], item["amount"], item["category_id"]),
        )


def create_or_update(db, user_id, payload, tx_id=None):
    description = str(payload.get("description", "")).strip()
    if not description:
        raise ValidationError("descriptionは必須です。")

    type_ = payload.get("type") or "expense"
    if type_ not in VALID_TYPES:
        raise ValidationError("typeはincomeまたはexpenseで指定してください。")

    items = _validate_items(payload.get("items"))

    if items:
        amount = sum(item["amount"] for item in items)
    else:
        amount = _coerce_amount(payload.get("amount"), "amountは0以上の数値で指定してください。")

    date_value = parse_date(payload.get("date"))

    payment_method_id = _coerce_id_lenient(payload.get("payment_method_id"))
    if type_ == "income":
        payment_method_id = None

    category_id = _coerce_id_lenient(payload.get("category_id"))
    if category_id is None and items and type_ == "expense":
        category_id = _most_frequent_category_id(items)

    memo = payload.get("memo")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if tx_id is not None:
        existing = db.execute(
            "SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
        ).fetchone()
        if existing is None:
            raise NotFoundError()
        db.execute(
            "UPDATE transactions SET date=?, type=?, description=?, category_id=?, "
            "payment_method_id=?, amount=?, memo=?, updated_at=? WHERE id=?",
            (
                date_value,
                type_,
                description,
                category_id,
                payment_method_id,
                amount,
                memo,
                now,
                tx_id,
            ),
        )
        _save_items(db, tx_id, items)
        db.commit()
        return tx_id

    cursor = db.execute(
        "INSERT INTO transactions (user_id, date, type, description, category_id, "
        "payment_method_id, amount, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, date_value, type_, description, category_id, payment_method_id, amount, memo),
    )
    new_id = cursor.lastrowid
    _save_items(db, new_id, items)
    db.commit()
    return new_id


def delete_transaction(db, user_id, tx_id):
    cursor = db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
    db.commit()
    return cursor.rowcount > 0
