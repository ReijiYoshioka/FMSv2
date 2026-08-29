import os


class Config:
    """環境変数から設定を読み込む（旧FMSのconfig.php.example相当）。"""

    SECRET_KEY = os.environ.get("FMS_SECRET_KEY", "")
    DATABASE_PATH = os.environ.get("FMS_DB_PATH", "instance/fms.db")
    ACCESS_LOG_PATH = os.environ.get("FMS_LOG_PATH", "logs/app_access_log.txt")
    HEALTHCHECK_TOKEN = os.environ.get("FMS_HEALTHCHECK_TOKEN", "")
    FORCE_HTTPS = os.environ.get("FMS_FORCE_HTTPS", "0") == "1"

    GEMINI_API_KEY = os.environ.get("FMS_GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("FMS_GEMINI_MODEL", "gemini-3.5-flash-lite")
    RECEIPT_DAILY_LIMIT = int(os.environ.get("FMS_RECEIPT_DAILY_LIMIT", "30"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TESTING = False


class TestConfig(Config):
    SECRET_KEY = "test-secret-key"
    TESTING = True
