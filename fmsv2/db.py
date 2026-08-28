import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path):
    """schema.sql + seed.sql を実行してDBを初期化する。

    本番の初回セットアップとテストのfixtureの両方から呼ばれる。
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        seed_sql = (Path(__file__).parent / "seed.sql").read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        conn.commit()
    finally:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
