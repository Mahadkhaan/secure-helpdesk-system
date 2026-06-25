from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request
from flask_login import LoginManager, current_user
from models import User, Category, db
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from config import Config
from utils.logging_config import configure_logging


DEFAULT_CATEGORIES = ['Software', 'Hardware', 'Network', 'Account', 'Other']


def _ensure_password_column_width():
    """On PostgreSQL, widen User.password to TEXT if it's still VARCHAR(128).

    db.create_all() never alters existing columns, so a database that was
    created before this fix still has VARCHAR(128). This function inspects the
    live column and issues ALTER TABLE if needed. Safe to call on every startup:
    if the column is already TEXT the function returns immediately.
    SQLite does not enforce VARCHAR length, so nothing is done there.
    """
    from sqlalchemy import inspect, text
    if db.engine.dialect.name != 'postgresql':
        return
    inspector = inspect(db.engine)
    if 'user' not in inspector.get_table_names():
        return
    cols = {c['name']: c for c in inspector.get_columns('user')}
    col_type = cols.get('password', {}).get('type')
    if col_type is None:
        return
    # TEXT has no length attribute value; VARCHAR(128) has length=128.
    if getattr(col_type, 'length', None) is not None:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE "user" ALTER COLUMN password TYPE TEXT'))
            conn.commit()


def _seed_default_categories():
    """Insert any missing default categories. Safe to call repeatedly."""
    for name in DEFAULT_CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    db.session.commit()


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

    # Security headers — applied to every response via after_request.
    # style-src needs 'unsafe-inline' because templates use inline style="" attributes;
    # script-src intentionally has no 'unsafe-inline'.
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

    # Create missing tables and seed defaults on every startup.
    # db.create_all() is a no-op for tables that already exist, so it is safe
    # to run alongside Flask-Migrate — migrations remain the source of truth
    # for schema changes, but this ensures the schema exists even when
    # flask db upgrade has not been run (e.g. Render free tier, fresh clone).
    with app.app_context():
        db.create_all()
        _ensure_password_column_width()
        _seed_default_categories()

    return app


app = create_app()

if __name__ == '__main__':
    app.run()
