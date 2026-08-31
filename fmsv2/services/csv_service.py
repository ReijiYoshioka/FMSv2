import csv
import io

from ..utils import numbers
from . import transactions_repo
from .errors import ValidationError

MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_ERRORS = 10
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
CSV_HEADERS = ["date", "type", "description", "category", "payment_method", "amount", "memo"]


def _csv_safe(value):
    text = "" if value is None else str(value)
    if text and text[0] in DANGEROUS_PREFIXES:
        return "'" + text
    return text


def export_rows(
    db, user_id, month, q=None, type_=None, category_id=None, min_amount=None, max_amount=None
):
    txs = transactions_repo.list_transactions(
        db,
        user_id,
        month,
        q=q,
        type_=type_,
        category_id=category_id,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    category_rows = db.execute("SELECT id, name FROM categories").fetchall()
    payment_rows = db.execute("SELECT id, name FROM payment_methods").fetchall()
    category_names = {r["id"]: r["name"] for r in category_rows}
    payment_names = {r["id"]: r["name"] for r in payment_rows}
    rows = []
    for tx in txs:
        rows.append(
            {
                "date": tx["date"],
                "type": tx["type"],
                "description": tx["description"],
                "category": category_names.get(tx["category_id"], ""),
                "payment_method": payment_names.get(tx["payment_method_id"], ""),
                "amount": tx["amount"],
                "memo": tx["memo"] or "",
            }
        )
    return rows


def build_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)
    for row in rows:
        writer.writerow([_csv_safe(row[key]) for key in CSV_HEADERS])
    return "﻿" + buffer.getvalue()


def import_csv(db, user_id, file_storage):
    raw = file_storage.read()
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValidationError("ファイルサイズは2MB以内にしてください。")

    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {"success": True, "inserted": 0, "skipped": 0, "errors": []}

    if rows[0] and rows[0][0].strip().lower() == "date":
        rows = rows[1:]

    categories = {
        r["name"]: r["id"] for r in db.execute("SELECT id, name FROM categories").fetchall()
    }
    payments = {
        r["name"]: r["id"] for r in db.execute("SELECT id, name FROM payment_methods").fetchall()
    }

    to_insert = []
    skipped = 0
    errors = []

    for i, row in enumerate(rows, start=1):
        # 完全な空行は旧PHP版と同様にskipped/errorsへ数えず無条件でスキップする。
        if len(row) == 0 or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) < 6:
            skipped += 1
            if len(errors) < MAX_ERRORS:
                errors.append(f"{i}行目: 列数が不足しています。")
            continue

        date_raw, type_raw, description, category_name, payment_name, amount_raw = row[:6]
        memo = row[6] if len(row) > 6 else ""

        try:
            date_value = transactions_repo.parse_date(date_raw)
        except ValidationError:
            skipped += 1
            if len(errors) < MAX_ERRORS:
                errors.append(f"{i}行目: dateが不正です。")
            continue

        description = description.strip()
        if not description:
            skipped += 1
            if len(errors) < MAX_ERRORS:
                errors.append(f"{i}行目: descriptionが空です。")
            continue

        amount = numbers.to_valid_amount(amount_raw)
        if amount is None:
            skipped += 1
            if len(errors) < MAX_ERRORS:
                errors.append(f"{i}行目: amountが不正です。")
            continue

        type_value = "income" if type_raw.strip().lower() == "income" else "expense"
        category_id = categories.get(category_name.strip())
        payment_method_id = payments.get(payment_name.strip())
        if type_value == "income":
            payment_method_id = None

        to_insert.append(
            (
                user_id,
                date_value,
                type_value,
                description,
                category_id,
                payment_method_id,
                amount,
                memo,
            )
        )

    duplicates = 0
    if to_insert:
        dates = [record[1] for record in to_insert]
        existing_rows = db.execute(
            "SELECT date, amount, description FROM transactions "
            "WHERE user_id = ? AND date >= ? AND date <= ?",
            (user_id, min(dates), max(dates)),
        ).fetchall()
        existing_keys = {(r["date"], r["amount"], r["description"]) for r in existing_rows}
        filtered = []
        for record in to_insert:
            key = (record[1], record[6], record[3])  # date_value, amount, description
            if key in existing_keys:
                duplicates += 1
                continue
            filtered.append(record)
        to_insert = filtered

    for record in to_insert:
        db.execute(
            "INSERT INTO transactions (user_id, date, type, description, category_id, "
            "payment_method_id, amount, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            record,
        )
    db.commit()

    return {
        "success": True,
        "inserted": len(to_insert),
        "skipped": skipped,
        "duplicates": duplicates,
        "errors": errors,
    }
