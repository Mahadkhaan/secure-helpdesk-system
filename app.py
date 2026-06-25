from dotenv import load_dotenv
load_dotenv()  # populate os.environ from .env before Config is evaluated

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from models import User, Ticket, Comment, Category, db
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from config import Config
from forms import (AdminLoginForm, UserLoginForm, AdminRegisterForm,
                   UserRegisterForm, TicketForm, CommentForm, VALID_STATUS_VALUES)

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'home'


# ── Logging ────────────────────────────────────────────────────────────────────

def _configure_logging(application):
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'helpdesk.log'),
        maxBytes=1_048_576,  # 1 MB per file
        backupCount=5
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    application.logger.setLevel(logging.INFO)
    application.logger.addHandler(file_handler)
    application.logger.addHandler(console_handler)


_configure_logging(app)


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(400)
def bad_request(_):
    # Most 400s from this app are Flask-WTF CSRF rejections.
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


# ── User loader ────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Public routes ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('home.html')


@app.route('/choose_role/<action>')
def choose_role(action):
    if action not in ['login', 'register']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('home'))
    return render_template(
        'choose_role.html',
        action=action,
        admin_endpoint=f'admin_{action}',
        user_endpoint=f'user_{action}'
    )


# ── Admin auth ─────────────────────────────────────────────────────────────────

@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='Admin').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            app.logger.info(
                '[AUTH] Admin login success: user=%s ip=%s',
                user.username, request.remote_addr
            )
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_dashboard'))
        app.logger.warning(
            '[AUTH] Admin login failure: attempted_user=%s ip=%s',
            form.username.data, request.remote_addr
        )
        flash('Invalid admin credentials.', 'danger')
    return render_template('login_admin.html', form=form)


@app.route('/register/admin', methods=['GET', 'POST'])
def admin_register():
    reg_code = app.config.get('ADMIN_REGISTRATION_CODE', '')
    if not reg_code:
        app.logger.warning(
            '[AUTH] Admin registration attempted but disabled: ip=%s',
            request.remote_addr
        )
        flash('Admin registration is disabled. Contact an existing administrator.', 'danger')
        return redirect(url_for('home'))

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = AdminRegisterForm()
    if form.validate_on_submit():
        if form.registration_code.data != reg_code:
            app.logger.warning(
                '[AUTH] Admin registration with invalid code: attempted_user=%s ip=%s',
                form.username.data, request.remote_addr
            )
            flash('Invalid registration code.', 'danger')
            return render_template('register_admin.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('register_admin.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose another one.', 'danger')
            return render_template('register_admin.html', form=form)
        try:
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                role='Admin'
            )
            db.session.add(new_user)
            db.session.commit()
            app.logger.info('[AUTH] Admin registered: user=%s ip=%s',
                            new_user.username, request.remote_addr)
            flash('Admin registration successful. Please login.', 'success')
            return redirect(url_for('admin_login'))
        except Exception:
            db.session.rollback()
            app.logger.error('[DB] Admin registration DB error: user=%s',
                             form.username.data, exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')
    return render_template('register_admin.html', form=form)


# ── User auth ──────────────────────────────────────────────────────────────────

@app.route('/login/user', methods=['GET', 'POST'])
def user_login():
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='User').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            app.logger.info(
                '[AUTH] User login success: user=%s ip=%s',
                user.username, request.remote_addr
            )
            flash('User login successful.', 'success')
            return redirect(url_for('user_dashboard'))
        app.logger.warning(
            '[AUTH] User login failure: attempted_user=%s ip=%s',
            form.username.data, request.remote_addr
        )
        flash('Invalid user credentials.', 'danger')
    return render_template('login_user.html', form=form)


@app.route('/register/user', methods=['GET', 'POST'])
def user_register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = UserRegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('register_user.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose another one.', 'danger')
            return render_template('register_user.html', form=form)
        try:
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                role='User'
            )
            db.session.add(new_user)
            db.session.commit()
            app.logger.info('[AUTH] User registered: user=%s ip=%s',
                            new_user.username, request.remote_addr)
            flash('User registration successful. Please login.', 'success')
            return redirect(url_for('user_login'))
        except Exception:
            db.session.rollback()
            app.logger.error('[DB] User registration DB error: user=%s',
                             form.username.data, exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')
    return render_template('register_user.html', form=form)


@app.route('/logout')
@login_required
def logout():
    app.logger.info('[AUTH] Logout: user=%s role=%s ip=%s',
                    current_user.username, current_user.role, request.remote_addr)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))


# ── Admin dashboard ────────────────────────────────────────────────────────────

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        app.logger.warning(
            '[SECURITY] Non-admin accessed /admin/dashboard: user=%s ip=%s',
            current_user.username, request.remote_addr
        )
        abort(403)

    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    tickets = (Ticket.query.filter_by(category_id=category_id).all()
               if category_id else Ticket.query.all())

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            title            = (request.form.get('title') or '').strip()
            description      = (request.form.get('description') or '').strip()
            status           = (request.form.get('status') or '').strip()
            category_id_form = request.form.get('category_id', type=int)

            updated = False

            if title:
                if not (3 <= len(title) <= 100):
                    app.logger.warning(
                        '[VALIDATION] Invalid title length: len=%d user=%s ticket=%d',
                        len(title), current_user.username, ticket_id
                    )
                    flash('Title must be between 3 and 100 characters.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.title = title
                updated = True
            if description:
                if len(description) < 10:
                    app.logger.warning(
                        '[VALIDATION] Description too short: len=%d user=%s ticket=%d',
                        len(description), current_user.username, ticket_id
                    )
                    flash('Description must be at least 10 characters.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.description = description
                updated = True
            if status:
                if status not in VALID_STATUS_VALUES:
                    app.logger.warning(
                        '[VALIDATION] Invalid status value: status=%r user=%s ticket=%d',
                        status, current_user.username, ticket_id
                    )
                    flash('Invalid status value.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.status = status
                updated = True
            if category_id_form is not None:
                ticket.category_id = category_id_form
                updated = True

            if updated:
                try:
                    db.session.commit()
                    app.logger.info('[TICKET] Admin updated ticket: ticket_id=%d admin=%s',
                                    ticket_id, current_user.username)
                    flash('Ticket updated successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    app.logger.error('[DB] Error updating ticket %d', ticket_id, exc_info=True)
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                flash('No fields were provided to update.', 'warning')
            return redirect(url_for('admin_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)
            try:
                db.session.delete(ticket)
                db.session.commit()
                app.logger.warning('[TICKET] Admin deleted ticket: ticket_id=%d admin=%s',
                                   ticket_id, current_user.username)
                flash('Ticket deleted successfully.', 'success')
            except Exception:
                db.session.rollback()
                app.logger.error('[DB] Error deleting ticket %d', ticket_id, exc_info=True)
                flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('admin_dashboard'))

        elif action == 'add_comment':
            ticket_id = request.form.get('ticket_id', type=int)
            if ticket_id is None:
                flash('Ticket ID is missing.', 'danger')
                return redirect(url_for('admin_dashboard'))

            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                flash('Ticket not found.', 'danger')
                return redirect(url_for('admin_dashboard'))

            comment_form = CommentForm()
            if comment_form.validate():
                try:
                    comment = Comment(
                        ticket_id=ticket_id,
                        user_id=current_user.id,
                        content=comment_form.content.data
                    )
                    db.session.add(comment)
                    db.session.commit()
                    app.logger.info('[TICKET] Admin added comment: ticket_id=%d admin=%s',
                                    ticket_id, current_user.username)
                    flash('Comment added successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    app.logger.error('[DB] Error adding comment to ticket %d', ticket_id, exc_info=True)
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                app.logger.warning('[VALIDATION] Invalid comment: user=%s ticket=%d',
                                   current_user.username, ticket_id)
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('admin_dashboard'))

    tickets_with_user = []
    for t in tickets:
        user = User.query.get(t.user_id) if t.user_id else None
        category = Category.query.get(t.category_id)
        tickets_with_user.append((
            t,
            user.username if user else 'Unassigned',
            category.name if category else 'Unknown'
        ))

    comment_form = CommentForm()
    return render_template(
        'admin_dashboard.html',
        tickets=tickets_with_user,
        categories=categories,
        selected_category=category_id,
        comment_form=comment_form
    )


# ── Admin create ticket ────────────────────────────────────────────────────────

@app.route('/admin/create_ticket', methods=['GET', 'POST'])
@login_required
def admin_create_ticket():
    if current_user.role != 'Admin':
        app.logger.warning(
            '[SECURITY] Non-admin accessed /admin/create_ticket: user=%s ip=%s',
            current_user.username, request.remote_addr
        )
        abort(403)

    categories = Category.query.all()
    form = TicketForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        try:
            new_ticket = Ticket(
                title=form.title.data,
                description=form.description.data,
                status=form.status.data,
                created_at=datetime.now(timezone.utc),
                user_id=current_user.id,
                category_id=form.category_id.data,
                created_by='admin'
            )
            db.session.add(new_ticket)
            db.session.commit()
            app.logger.info(
                '[TICKET] Admin created ticket: ticket_id=%d title=%r admin=%s',
                new_ticket.id, new_ticket.title, current_user.username
            )
            flash('Admin ticket created successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception:
            db.session.rollback()
            app.logger.error('[DB] Error creating ticket for admin=%s',
                             current_user.username, exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('admin_create_ticket.html', form=form, categories=categories)


# ── User dashboard ─────────────────────────────────────────────────────────────

@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if current_user.role != 'User':
        app.logger.warning(
            '[SECURITY] Non-user accessed /user/dashboard: user=%s ip=%s',
            current_user.username, request.remote_addr
        )
        abort(403)

    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    tickets = (Ticket.query.filter_by(user_id=current_user.id, category_id=category_id).all()
               if category_id
               else Ticket.query.filter_by(user_id=current_user.id).all())

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            if ticket.user_id != current_user.id:
                app.logger.warning(
                    '[SECURITY] User attempted to update another user\'s ticket: '
                    'user=%s ticket_id=%d owner_id=%d ip=%s',
                    current_user.username, ticket_id, ticket.user_id, request.remote_addr
                )
                abort(403)

            title            = (request.form.get('title') or '').strip()
            description      = (request.form.get('description') or '').strip()
            category_id_form = request.form.get('category_id', type=int)
            # Users are not permitted to change ticket status — silently ignored.

            updated = False

            if title:
                if not (3 <= len(title) <= 100):
                    flash('Title must be between 3 and 100 characters.', 'danger')
                    return redirect(url_for('user_dashboard'))
                ticket.title = title
                updated = True
            if description:
                if len(description) < 10:
                    flash('Description must be at least 10 characters.', 'danger')
                    return redirect(url_for('user_dashboard'))
                ticket.description = description
                updated = True
            if category_id_form is not None:
                ticket.category_id = category_id_form
                updated = True

            if updated:
                try:
                    db.session.commit()
                    app.logger.info('[TICKET] User updated ticket: ticket_id=%d user=%s',
                                    ticket_id, current_user.username)
                    flash('Ticket updated successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    app.logger.error('[DB] Error updating ticket %d for user=%s',
                                     ticket_id, current_user.username, exc_info=True)
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                flash('No fields were provided to update.', 'warning')
            return redirect(url_for('user_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            if ticket.user_id != current_user.id:
                app.logger.warning(
                    '[SECURITY] User attempted to delete another user\'s ticket: '
                    'user=%s ticket_id=%d owner_id=%d ip=%s',
                    current_user.username, ticket_id, ticket.user_id, request.remote_addr
                )
                abort(403)

            try:
                db.session.delete(ticket)
                db.session.commit()
                app.logger.warning('[TICKET] User deleted ticket: ticket_id=%d user=%s',
                                   ticket_id, current_user.username)
                flash('Ticket deleted successfully.', 'success')
            except Exception:
                db.session.rollback()
                app.logger.error('[DB] Error deleting ticket %d for user=%s',
                                 ticket_id, current_user.username, exc_info=True)
                flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('user_dashboard'))

        elif action == 'add_comment':
            ticket_id = request.form.get('ticket_id', type=int)
            if ticket_id is None:
                flash('Ticket ID is missing.', 'danger')
                return redirect(url_for('user_dashboard'))

            ticket = Ticket.query.get(ticket_id)
            if not ticket or ticket.user_id != current_user.id:
                app.logger.warning(
                    '[SECURITY] User attempted to comment on unauthorized ticket: '
                    'user=%s ticket_id=%s ip=%s',
                    current_user.username, ticket_id, request.remote_addr
                )
                flash('Ticket not found or unauthorized.', 'danger')
                return redirect(url_for('user_dashboard'))

            comment_form = CommentForm()
            if comment_form.validate():
                try:
                    comment = Comment(
                        ticket_id=ticket_id,
                        user_id=current_user.id,
                        content=comment_form.content.data
                    )
                    db.session.add(comment)
                    db.session.commit()
                    app.logger.info('[TICKET] User added comment: ticket_id=%d user=%s',
                                    ticket_id, current_user.username)
                    flash('Comment added successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    app.logger.error('[DB] Error adding comment to ticket %d for user=%s',
                                     ticket_id, current_user.username, exc_info=True)
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                app.logger.warning('[VALIDATION] Invalid comment: user=%s ticket=%d',
                                   current_user.username, ticket_id)
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('user_dashboard'))

    comment_form = CommentForm()
    return render_template(
        'user_dashboard.html',
        tickets=tickets,
        categories=categories,
        selected_category=category_id,
        comment_form=comment_form
    )


# ── User create ticket ─────────────────────────────────────────────────────────

@app.route('/user/create_ticket', methods=['GET', 'POST'])
@login_required
def user_create_ticket():
    if current_user.role != 'User':
        app.logger.warning(
            '[SECURITY] Non-user accessed /user/create_ticket: user=%s ip=%s',
            current_user.username, request.remote_addr
        )
        abort(403)

    categories = Category.query.all()
    form = TicketForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        try:
            new_ticket = Ticket(
                title=form.title.data,
                description=form.description.data,
                status=form.status.data,
                created_at=datetime.now(timezone.utc),
                user_id=current_user.id,
                category_id=form.category_id.data,
                created_by='user'
            )
            db.session.add(new_ticket)
            db.session.commit()
            app.logger.info(
                '[TICKET] User created ticket: ticket_id=%d title=%r user=%s',
                new_ticket.id, new_ticket.title, current_user.username
            )
            flash('Ticket created successfully.', 'success')
            return redirect(url_for('user_dashboard'))
        except Exception:
            db.session.rollback()
            app.logger.error('[DB] Error creating ticket for user=%s',
                             current_user.username, exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('user_create_ticket.html', form=form, categories=categories)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
