from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request
from flask_login import LoginManager, current_user
from models import User, db
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from config import Config
from utils.logging_config import configure_logging


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CSRFProtect(app)
    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager(app)
    login_manager.login_view = 'main.home'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    configure_logging(app)

    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.user import user_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    # ── Security headers ───────────────────────────────────────────────────────
    # Applied to every response regardless of blueprint.
    # CSP notes:
    #   script-src: only 'self' and jsDelivr (Bootstrap JS) — no inline scripts exist
    #   style-src:  'unsafe-inline' is required because templates use inline style=""
    #               attributes (e.g. max-width, max-height); removing them is left as
    #               a future hardening step once a static CSS file is introduced
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        return response

    @app.errorhandler(400)
    def bad_request(_):
        actor = current_user.username if current_user.is_authenticated else 'anonymous'
        app.logger.warning(
            '[SECURITY] 400 Bad Request (possible CSRF): url=%s user=%s ip=%s',
            request.url, actor, request.remote_addr
        )
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(_):
        actor = current_user.username if current_user.is_authenticated else 'anonymous'
        app.logger.warning(
            '[SECURITY] 403 Forbidden: url=%s user=%s ip=%s',
            request.url, actor, request.remote_addr
        )
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(_):
        app.logger.info('[HTTP] 404 Not Found: %s', request.url)
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        app.logger.error(
            '[HTTP] 500 Internal Server Error: url=%s error=%s',
            request.url, str(e), exc_info=True
        )
        return render_template('errors/500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
