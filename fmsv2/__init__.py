from flask import Flask, session
from werkzeug.middleware.proxy_fix import ProxyFix

from . import cli, db
from .config import Config
from .logging_ import access_log
from .security import headers
from .security.csrf import csrf_token
from .utils.json_response import json_error


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"] and not app.config["TESTING"]:
        raise RuntimeError("FMS_SECRET_KEY が設定されていない。.env を確認する。")

    app.config["SESSION_COOKIE_SECURE"] = app.config["FORCE_HTTPS"]
    if not app.config["FORCE_HTTPS"] and not app.config["TESTING"]:
        app.logger.warning(
            "FMS_FORCE_HTTPS が未設定のため、セッションクッキーにSecure属性が付かない。"
            "HTTPSで運用している場合はFMS_FORCE_HTTPS=1を設定する。"
        )

    proxy_count = app.config["TRUSTED_PROXY_COUNT"]
    if proxy_count > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=proxy_count, x_proto=proxy_count, x_host=proxy_count
        )

    db.init_app(app)
    cli.init_app(app)
    headers.init_app(app)
    access_log.init_app(app)

    @app.context_processor
    def inject_template_globals():
        return {"csrf_token": csrf_token(), "current_username": session.get("username")}

    @app.errorhandler(413)
    def handle_payload_too_large(_e):
        return json_error("アップロードサイズが大きすぎます。", 413)

    from .blueprints import (
        api_account,
        api_budget,
        api_chat,
        api_csv,
        api_masters,
        api_places,
        api_receipts,
        api_recurring,
        api_summary,
        api_transactions,
        auth,
        healthcheck,
        pages,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(pages.bp)
    app.register_blueprint(api_transactions.bp)
    app.register_blueprint(api_summary.bp)
    app.register_blueprint(api_budget.bp)
    app.register_blueprint(api_recurring.bp)
    app.register_blueprint(api_masters.bp)
    app.register_blueprint(api_account.bp)
    app.register_blueprint(api_csv.bp)
    app.register_blueprint(api_receipts.bp)
    app.register_blueprint(api_places.bp)
    app.register_blueprint(api_chat.bp)
    app.register_blueprint(healthcheck.bp)

    return app
