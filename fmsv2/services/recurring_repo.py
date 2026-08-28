import sqlite3

from ..utils.dates import last_day_of_month
from .errors import NotFoundError, ValidationError

VALID_TYPES = ("income", "expense")


def list_recurring(db, user_id, month):
    rows = db.execute(
        "SELECT * FROM recurring_transactions WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    applied_rows = db.execute(
        "SELECT recurring_id FROM recurring_applications WHERE user_id = ? AND month = ?",
        (user_id, month),
    ).fetchall()
    applied_ids = {row["recurring_id"] for row in applied_rows}

    result = []
    for row in rows:
        entry = dict(row)
        entry["applied_this_month"] = row["id"] in applied_ids
        result.append(entry)
    return result


def _validate_payload(payload):
    description = str(payload.get("description", "")).strip()
    if not description:
        raise ValidationError("descriptionは必須です。")

    type_ = payload.get("type") or "expense"
    if type_ not in VALID_TYPES:
        raise ValidationError("typeはincomeまたはexpenseで指定してください。")

    try:
        amount = int(float(payload.get("amount")))
    except (TypeError, ValueError):
        raise ValidationError("amountは数値で指定してください。") from None
    if amount < 0:
        raise ValidationError("amountは0以上で指定してください。")

    try:
        day_of_month = int(payload.get("day_of_month"))
    except (TypeError, ValueError):
        raise ValidationError("day_of_monthは数値で指定してください。") from None
    if not 1 <= day_of_month <= 31:
        raise ValidationError("day_of_monthは1〜31で指定してください。")

    payment_method_id = payload.get("payment_method_id")
    if type_ == "income":
        payment_method_id = None

    return {
        "description": description,
        "type": type_,
        "amount": amount,
        "day_of_month": day_of_month,
        "category_id": payload.get("category_id"),
        "payment_method_id": payment_method_id,
        "memo": payload.get("memo"),
        # 旧版は`!empty($input['active'])`相当で、activeキー省略時は常に無効(0)扱い。
        # 更新時もフルスナップショット送信が前提のため、省略すれば無効化される。
        "active": 1 if payload.get("active") else 0,
    }


def create_or_update(db, user_id, payload, recurring_id=None):
    data = _validate_payload(payload)

    if recurring_id is not None:
        existing = db.execute(
            "SELECT id FROM recurring_transactions WHERE id = ? AND user_id = ?",
            (recurring_id, user_id),
        ).fetchone()
        if existing is None:
            raise NotFoundError()
        db.execute(
            "UPDATE recurring_transactions SET day_of_month=?, type=?, description=?, "
            "category_id=?, payment_method_id=?, amount=?, memo=?, active=? WHERE id=?",
            (
                data["day_of_month"],
                data["type"],
                data["description"],
                data["category_id"],
                data["payment_method_id"],
                data["amount"],
                data["memo"],
                data["active"],
                recurring_id,
            ),
        )
        db.commit()
        return recurring_id

    cursor = db.execute(
        "INSERT INTO recurring_transactions (user_id, day_of_month, type, description, "
        "category_id, payment_method_id, amount, memo, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            data["day_of_month"],
            data["type"],
            data["description"],
            data["category_id"],
            data["payment_method_id"],
            data["amount"],
            data["memo"],
            data["active"],
        ),
    )
    db.commit()
    return cursor.lastrowid


def delete_recurring(db, user_id, recurring_id):
    cursor = db.execute(
        "DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?",
        (recurring_id, user_id),
    )
    db.commit()
    return cursor.rowcount > 0


def apply_all(db, user_id, month):
    year, month_num = map(int, month.split("-"))
    templates = db.execute(
        "SELECT * FROM recurring_transactions WHERE user_id = ? AND active = 1", (user_id,)
    ).fetchall()

    applied = 0
    already = 0
    for template in templates:
        try:
            db.execute(
                "INSERT INTO recurring_applications (user_id, recurring_id, month) "
                "VALUES (?, ?, ?)",
                (user_id, template["id"], month),
            )
        except sqlite3.IntegrityError:
            db.rollback()
            already += 1
            continue

        day = min(template["day_of_month"], last_day_of_month(year, month_num))
        date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
        cursor = db.execute(
            "INSERT INTO transactions (user_id, date, type, description, category_id, "
            "payment_method_id, amount, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                date_str,
                template["type"],
                template["description"],
                template["category_id"],
                template["payment_method_id"],
                template["amount"],
                template["memo"],
            ),
        )
        tx_id = cursor.lastrowid
        db.execute(
            "UPDATE recurring_applications SET transaction_id = ? "
            "WHERE user_id = ? AND recurring_id = ? AND month = ?",
            (tx_id, user_id, template["id"], month),
        )
        db.commit()
        applied += 1

    return {"applied": applied, "already": already, "total": len(templates)}
