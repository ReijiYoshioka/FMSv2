from datetime import datetime, timedelta
from pathlib import Path

from fmsv2.logging_ import access_log


def test_request_writes_begin_and_end_lines(client, app):
    client.get("/healthcheck?token=test-healthcheck-token")
    log_text = app.config["ACCESS_LOG_PATH"]
    with open(log_text, encoding="utf-8") as f:
        lines = f.readlines()
    assert any(" BEGIN " in line for line in lines)
    assert any(" END " in line for line in lines)


def test_prune_removes_lines_older_than_retention(app):
    log_path = app.config["ACCESS_LOG_PATH"]
    old_ts = (datetime.now() - timedelta(days=access_log.RETENTION_DAYS + 10)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    recent_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"{old_ts} BEGIN method=GET path=/old token=aaaa\n")
        f.write(f"{recent_ts} BEGIN method=GET path=/new token=bbbb\n")

    with app.app_context():
        access_log.prune_old_entries()

    with open(log_path, encoding="utf-8") as f:
        remaining = f.read()
    assert "/old" not in remaining
    assert "/new" in remaining
