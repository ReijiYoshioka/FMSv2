import sqlite3

from ..utils import numbers
from ..utils.dates import month_range, shift_month
from . import summary_repo
from .errors import ValidationError


def get_budget_status(db, user_id, month):
    start, end = month_range(month)
    spent_rows = summary_repo.category_expense_amounts(db, user_id, start, end)
    spent_by_category = {row["category_id"]: row["value"] for row in spent_rows}

    budget_rows = db.execute(
        "SELECT b.category_id, b.amount, c.name AS category "
        "FROM budgets b JOIN categories c ON c.id = b.category_id "
        "WHERE b.user_id = ? AND b.month = ? ORDER BY c.id",
        (user_id, month),
    ).fetchall()

    items = []
    total_budget = 0
    total_spent = 0
    for row in budget_rows:
        budget_amount = row["amount"]
        spent = spent_by_category.get(row["category_id"], 0)
        ratio = round(spent / budget_amount * 100) if budget_amount > 0 else 0
        items.append(
            {
                "category_id": row["category_id"],
                "category": row["category"],
                "budget": budget_amount,
                "spent": spent,
                "remaining": budget_amount - spent,
                "ratio": ratio,
            }
        )
        total_budget += budget_amount
        total_spent += spent

    return {"items": items, "total_budget": total_budget, "total_spent": total_spent}


def _to_valid_category_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _upsert(db, user_id, category_id, month, amount):
    """amount==0は削除として扱う（旧PHP版と同じ方針）。戻り値はdeletedされたかどうか。"""
    if amount == 0:
        db.execute(
            "DELETE FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?",
            (user_id, category_id, month),
        )
        return True
    try:
        db.execute(
            "INSERT INTO budgets (user_id, category_id, month, amount) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, category_id, month) DO UPDATE SET amount = excluded.amount",
            (user_id, category_id, month, amount),
        )
    except sqlite3.IntegrityError:
        raise ValidationError("指定されたカテゴリーが見つかりません。", 404) from None
    return False


def save_items(db, user_id, month, items):
    """不正な要素（category_id/amountが数値でない、amountが負数、削除済みカテゴリー）は旧版同様に静かにスキップする。"""
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        category_id = _to_valid_category_id(item.get("category_id"))
        if category_id is None:
            continue
        amount = numbers.to_valid_amount(item.get("amount", 0))
        if amount is None:
            continue
        try:
            _upsert(db, user_id, category_id, month, amount)
        except ValidationError:
            continue
        saved += 1
    db.commit()
    return saved


def save_single(db, user_id, month, category_id, amount):
    category_id = _to_valid_category_id(category_id)
    amount = numbers.to_valid_amount(amount)
    if category_id is None or amount is None:
        raise ValidationError("有効な予算額を入力してください。")
    deleted = _upsert(db, user_id, category_id, month, amount)
    db.commit()
    return deleted


def delete_budget(db, user_id, month, category_id):
    cursor = db.execute(
        "DELETE FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?",
        (user_id, category_id, month),
    )
    db.commit()
    return cursor.rowcount > 0


def copy_prev_month(db, user_id, month):
    prev_month = shift_month(month, -1)
    rows = db.execute(
        "SELECT category_id, amount FROM budgets WHERE user_id = ? AND month = ?",
        (user_id, prev_month),
    ).fetchall()
    for row in rows:
        _upsert(db, user_id, row["category_id"], month, row["amount"])
    db.commit()
    return len(rows)
