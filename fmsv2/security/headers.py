CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "font-src 'self' https://cdnjs.cloudflare.com; "
    # テンプレート側にまだインラインscript/style属性が残っているため'unsafe-inline'が必要。
    # 将来的にインラインを排除できればnonce/hashベースに強化する。
    "script-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


def init_app(app):
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = CSP
        if app.config["FORCE_HTTPS"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
