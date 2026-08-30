import os


class Config:
    """環境変数から設定を読み込む（旧FMSのconfig.php.example相当）。"""

    SECRET_KEY = os.environ.get("FMS_SECRET_KEY", "")
    DATABASE_PATH = os.environ.get("FMS_DB_PATH", "instance/fms.db")
    ACCESS_LOG_PATH = os.environ.get("FMS_LOG_PATH", "logs/app_access_log.txt")
    HEALTHCHECK_TOKEN = os.environ.get("FMS_HEALTHCHECK_TOKEN", "")
    FORCE_HTTPS = os.environ.get("FMS_FORCE_HTTPS", "0") == "1"
    # リバースプロキシを何段挟んでいるか。0なら X-Forwarded-For 等を一切信用しない。
    TRUSTED_PROXY_COUNT = int(os.environ.get("FMS_TRUSTED_PROXY_COUNT", "0"))

    GEMINI_API_KEY = os.environ.get("FMS_GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("FMS_GEMINI_MODEL", "gemini-3.5-flash-lite")
    RECEIPT_DAILY_LIMIT = int(os.environ.get("FMS_RECEIPT_DAILY_LIMIT", "30"))
    PLACE_SUGGEST_DAILY_LIMIT = int(os.environ.get("FMS_PLACE_SUGGEST_DAILY_LIMIT", "200"))
    CHAT_DAILY_LIMIT = int(os.environ.get("FMS_CHAT_DAILY_LIMIT", "60"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TESTING = False

    # 個々の機能のサイズ上限（CSV 2MB、レシート画像8MB）より大きい値にして、
    # multipartのオーバーヘッド込みでも機能側のチェックが先に発火するようにする。
    # これが無いとWerkzeugがリクエストボディサイズを無制限に受け付けてしまう。
    MAX_CONTENT_LENGTH = int(os.environ.get("FMS_MAX_CONTENT_LENGTH", str(12 * 1024 * 1024)))


class TestConfig(Config):
    SECRET_KEY = "test-secret-key"
    TESTING = True
