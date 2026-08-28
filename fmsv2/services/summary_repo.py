from ..utils.dates import month_range, year_range

_CATEGORY_SQL = """
SELECT sub.category_id AS category_id, COALESCE(c.name, '未分類') AS category,
       SUM(sub.amount) AS value
FROM (
    SELECT ti.category_id AS category_id, ti.amount AS amount
    FROM transaction_items ti
    JOIN transactions t ON t.id = ti.transaction_id
    WHERE t.user_id = ? AND t.type = 'expense' AND t.date >= ? AND t.date < ?

    UNION ALL

    SELECT t.category_id AS category_id, t.amount AS amount
    FROM transactions t
    WHERE t.user_id = ? AND t.type = 'expense' AND t.date >= ? AND t.date < ?
      AND NOT EXISTS (SELECT 1 FROM transaction_items ti2 WHERE ti2.transaction_id = t.id)
) sub
LEFT JOIN categories c ON c.id = sub.category_id
GROUP BY sub.category_id
ORDER BY value DESC
"""

_PAYMENT_SQL = """
SELECT COALESCE(pm.name, '未設定') AS payment_method, SUM(t.amount) AS value
FROM transactions t
LEFT JOIN payment_methods pm ON pm.id = t.payment_method_id
WHERE t.user_id = ? AND t.type = 'expense' AND t.date >= ? AND t.date < ?
GROUP BY t.payment_method_id
ORDER BY value DESC
"""


def _stats(db, user_id, start, end):
    rows = db.execute(
        "SELECT type, SUM(amount) AS total FROM transactions "
        "WHERE user_id = ? AND date >= ? AND date < ? GROUP BY type",
        (user_id, start, end),
    ).fetchall()
    totals = {row["type"]: row["total"] for row in rows}
    income = totals.get("income", 0) or 0
    expense = totals.get("expense", 0) or 0
    return {"income": income, "expense": expense, "balance": income - expense}


def monthly_stats(db, user_id, month):
    start, end = month_range(month)
    return _stats(db, user_id, start, end)


def annual_stats(db, user_id, year):
    start, end = year_range(year)
    return _stats(db, user_id, start, end)


def category_expense_amounts(db, user_id, start, end):
    """指定期間のカテゴリー別支出金額を返す。内訳(transaction_items)があればitem単位の
    category_id、無ければ本体のcategory_idで集計し、budget_repoからも再利用される。
    """
    rows = db.execute(_CATEGORY_SQL, (user_id, start, end, user_id, start, end)).fetchall()
    return [dict(r) for r in rows]


def category_chart(db, user_id, month):
    start, end = month_range(month)
    return category_expense_amounts(db, user_id, start, end)


def annual_category_chart(db, user_id, year):
    start, end = year_range(year)
    return category_expense_amounts(db, user_id, start, end)


def payment_chart(db, user_id, month):
    start, end = month_range(month)
    rows = db.execute(_PAYMENT_SQL, (user_id, start, end)).fetchall()
    return [dict(r) for r in rows]


def annual_payment_chart(db, user_id, year):
    start, end = year_range(year)
    rows = db.execute(_PAYMENT_SQL, (user_id, start, end)).fetchall()
    return [dict(r) for r in rows]


def annual_trend(db, user_id, year):
    start, end = year_range(year)
    rows = db.execute(
        "SELECT strftime('%Y-%m', date) AS ym, type, SUM(amount) AS total "
        "FROM transactions WHERE user_id = ? AND date >= ? AND date < ? "
        "GROUP BY ym, type",
        (user_id, start, end),
    ).fetchall()
    totals = {(row["ym"], row["type"]): row["total"] for row in rows}
    labels = [f"{year}-{m:02d}" for m in range(1, 13)]
    income = [totals.get((ym, "income"), 0) or 0 for ym in labels]
    expense = [totals.get((ym, "expense"), 0) or 0 for ym in labels]
    return {"labels": labels, "income": income, "expense": expense}
