import sqlite3

import pytest

EXPECTED_TABLES = {
    "users",
    "login_attempts",
    "categories",
    "payment_methods",
    "transactions",
    "transaction_items",
    "recurring_transactions",
    "recurring_applications",
    "budgets",
}


def test_all_tables_created(app):
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    table_names = {row[0] for row in rows}
    assert EXPECTED_TABLES <= table_names


def test_seed_master_data_loaded(app):
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    category_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    payment_count = conn.execute("SELECT COUNT(*) FROM payment_methods").fetchone()[0]
    conn.close()
    assert category_count == 13
    assert payment_count == 8


def test_foreign_keys_enforced(app):
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT INTO users (username, password_hash) VALUES ('taro', 'hash')")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (user_id, date, type, description, amount) "
            "VALUES (9999, '2026-08-01', 'expense', 'test', 100)"
        )
    conn.close()
