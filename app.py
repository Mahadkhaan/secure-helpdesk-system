from dotenv import load_dotenv
load_dotenv()

import click
from flask import Flask, render_template, request
from flask_login import LoginManager, current_user
from models import User, Category, Ticket, Comment, db
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

    @app.cli.command('seed-demo-data')
    def seed_demo_data():
        """Create clearly labelled demo accounts, tickets, and comments.

        Passwords are generated randomly at runtime and printed once to the
        terminal. Missing records are created; existing records are never
        altered or deleted. Safe to re-run after partial deletion.
        """
        import secrets
        import string
        from werkzeug.security import generate_password_hash

        def _make_password():
            """16-char random password that meets the app's own complexity rules."""
            chars = string.ascii_letters + string.digits + '!@#$%^&*'
            while True:
                pwd = ''.join(secrets.choice(chars) for _ in range(16))
                if (any(c.isupper() for c in pwd)
                        and any(c.islower() for c in pwd)
                        and any(c.isdigit() for c in pwd)
                        and any(c in '!@#$%^&*' for c in pwd)):
                    return pwd

        cats = {c.name: c for c in Category.query.all()}
        if not cats:
            click.echo('No categories found. Start the app once first so categories are seeded.')
            return

        hw  = cats.get('Hardware') or next(iter(cats.values()))
        net = cats.get('Network')  or hw
        acc = cats.get('Account')  or hw
        sw  = cats.get('Software') or hw

        # ── Users: create only those that do not already exist ────────────────
        new_credentials = []
        for username, email, role in [
            ('demo_admin', 'demo.admin@helpdesk.example', 'Admin'),
            ('demo_user1', 'demo.user1@helpdesk.example', 'User'),
            ('demo_user2', 'demo.user2@helpdesk.example', 'User'),
        ]:
            if not User.query.filter_by(username=username).first():
                pwd = _make_password()
                db.session.add(User(
                    username=username,
                    email=email,
                    password=generate_password_hash(pwd),
                    role=role,
                ))
                new_credentials.append((username, role, pwd))
        db.session.flush()

        # ── Tickets: create only those that do not already exist ──────────────
        def _get_user(username):
            return User.query.filter_by(username=username).first()

        new_tickets = 0
        for title, description, status, owner_name, cat in [
            ('[DEMO] Printer not responding',
             'The office printer on Floor 2 is offline and not accepting print jobs. Restart was attempted with no success.',
             'Open', 'demo_user1', hw),
            ('[DEMO] VPN drops after 10 minutes',
             'Remote VPN connection disconnects automatically after approximately 10 minutes of inactivity. Affects all remote workers.',
             'In Progress', 'demo_user2', net),
            ('[DEMO] Password reset needed',
             'User account locked after too many failed login attempts. Requires admin password reset.',
             'Closed', 'demo_user1', acc),
            ('[DEMO] Software licence renewal',
             'Annual licence for the design suite expires in 14 days. Please raise a purchase order to renew before the deadline.',
             'Open', 'demo_admin', sw),
        ]:
            if not Ticket.query.filter_by(title=title).first():
                owner = _get_user(owner_name)
                if owner is None:
                    click.echo(f'  Skipping ticket {title!r}: owner {owner_name!r} not found.')
                    continue
                db.session.add(Ticket(
                    title=title,
                    description=description,
                    status=status,
                    user_id=owner.id,
                    category_id=cat.id,
                    created_by='admin' if owner.role == 'Admin' else 'user',
                ))
                new_tickets += 1
        db.session.flush()

        # ── Comments: one per ticket, skip if admin already commented ─────────
        admin = _get_user('demo_admin')
        new_comments = 0
        if admin:
            for ticket_title, content in [
                ('[DEMO] Printer not responding',
                 'Checked hardware — print queue is jammed. Will clear the spooler and restart the service.'),
                ('[DEMO] VPN drops after 10 minutes',
                 'VPN idle-timeout has been extended on the server. Please reconnect and confirm this resolves the issue.'),
                ('[DEMO] Password reset needed',
                 'Password has been reset. Please log in and change it immediately.'),
            ]:
                ticket = Ticket.query.filter_by(title=ticket_title).first()
                if ticket and not Comment.query.filter_by(
                        ticket_id=ticket.id, user_id=admin.id).first():
                    db.session.add(Comment(
                        content=content,
                        user_id=admin.id,
                        ticket_id=ticket.id,
                    ))
                    new_comments += 1
        db.session.commit()

        # ── Output ────────────────────────────────────────────────────────────
        if not new_credentials and not new_tickets and not new_comments:
            click.echo('Demo data already present — nothing changed.')
            return

        click.echo('Demo data seeded:')
        if new_credentials:
            click.echo(f'  Users created:    {len(new_credentials)}')
        if new_tickets:
            click.echo(f'  Tickets created:  {new_tickets}')
        if new_comments:
            click.echo(f'  Comments created: {new_comments}')

        if new_credentials:
            click.echo('')
            click.echo('Generated credentials (save these now — will not be shown again):')
            for username, role, pwd in new_credentials:
                click.echo(f'  {username:<12} [{role:<5}] : {pwd}')
            click.echo('')
            click.echo('WARNING: Delete or change these accounts before real use.')

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
