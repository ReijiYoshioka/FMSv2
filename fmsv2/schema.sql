-- FMSv2 スキーマ定義（旧FMS `FMS-main/web/fms/sql/init.sql` のMariaDB定義をSQLiteへ移植）
-- 接続直後に `PRAGMA foreign_keys = ON;` を実行しないと外部キー制約が無視されるので、
-- db.py 側で必ず実行すること（このファイル自体は毎接続で再実行されないため冒頭のPRAGMAは意味を持たない）。

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    username TEXT,
    success INTEGER NOT NULL DEFAULT 0 CHECK (success IN (0, 1)),
    attempted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_time ON login_attempts (ip_address, attempted_at);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 50)
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 50)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 200),
    category_id INTEGER REFERENCES categories (id) ON DELETE SET NULL,
    payment_method_id INTEGER REFERENCES payment_methods (id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    memo TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions (user_id, date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions (category_id);
CREATE INDEX IF NOT EXISTS idx_tx_payment_method ON transactions (payment_method_id);

CREATE TABLE IF NOT EXISTS transaction_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions (id) ON DELETE CASCADE,
    item_name TEXT NOT NULL CHECK (length(item_name) BETWEEN 1 AND 200),
    amount INTEGER NOT NULL,
    category_id INTEGER REFERENCES categories (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_items_transaction ON transaction_items (transaction_id);

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    day_of_month INTEGER NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 200),
    category_id INTEGER REFERENCES categories (id) ON DELETE SET NULL,
    payment_method_id INTEGER REFERENCES payment_methods (id) ON DELETE SET NULL,
    amount INTEGER NOT NULL,
    memo TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_recurring_user ON recurring_transactions (user_id);

CREATE TABLE IF NOT EXISTS recurring_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    recurring_id INTEGER NOT NULL REFERENCES recurring_transactions (id) ON DELETE CASCADE,
    month TEXT NOT NULL CHECK (length(month) = 7),
    transaction_id INTEGER REFERENCES transactions (id) ON DELETE SET NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, recurring_id, month)
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
    month TEXT NOT NULL CHECK (length(month) = 7),
    amount INTEGER NOT NULL,
    UNIQUE (user_id, category_id, month)
);
CREATE INDEX IF NOT EXISTS idx_budgets_user_month ON budgets (user_id, month);
