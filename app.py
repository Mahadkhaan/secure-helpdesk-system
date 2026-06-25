from dotenv import load_dotenv
load_dotenv()  # populate os.environ from .env before Config is evaluated

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('home.html')

@app.route('/choose_role/<action>')
def choose_role(action):
    if action not in ['login', 'register']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('home'))
    admin_endpoint = f"admin_{action}"
    user_endpoint = f"user_{action}"
    return render_template('choose_role.html', action=action, admin_endpoint=admin_endpoint, user_endpoint=user_endpoint)

# Admin login/register routes
@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='Admin').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')
    return render_template('login_admin.html', form=form)

@app.route('/register/admin', methods=['GET', 'POST'])
def admin_register():
    # Block entirely when no registration code has been configured.
    reg_code = app.config.get('ADMIN_REGISTRATION_CODE', '')
    if not reg_code:
        flash('Admin registration is disabled. Contact an existing administrator.', 'danger')
        return redirect(url_for('home'))

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = AdminRegisterForm()
    if form.validate_on_submit():
        # Validate the secret code before touching the database.
        if form.registration_code.data != reg_code:
            flash('Invalid registration code.', 'danger')
            return render_template('register_admin.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('register_admin.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose another one.', 'danger')
            return render_template('register_admin.html', form=form)
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            role='Admin'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Admin registration successful. Please login.', 'success')
        return redirect(url_for('admin_login'))
    return render_template('register_admin.html', form=form)

# User login/register routes
@app.route('/login/user', methods=['GET', 'POST'])
def user_login():
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='User').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('User login successful.', 'success')
            return redirect(url_for('user_dashboard'))
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
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            role='User'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User registration successful. Please login.', 'success')
        return redirect(url_for('user_login'))
    return render_template('register_user.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

# Admin dashboard route - full ticket management
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        abort(403)

    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    tickets = Ticket.query.filter_by(category_id=category_id).all() if category_id else Ticket.query.all()

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
                    flash('Title must be between 3 and 100 characters.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.title = title
                updated = True
            if description:
                if len(description) < 10:
                    flash('Description must be at least 10 characters.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.description = description
                updated = True
            if status:
                if status not in VALID_STATUS_VALUES:
                    flash('Invalid status value.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                ticket.status = status
                updated = True
            if category_id_form is not None:
                ticket.category_id = category_id_form
                updated = True

            if updated:
                db.session.commit()
                flash('Ticket updated successfully.', 'success')
            else:
                flash('No fields were provided to update.', 'warning')

            return redirect(url_for('admin_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)
            db.session.delete(ticket)
            db.session.commit()
            flash('Ticket deleted successfully.', 'success')
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
                comment = Comment(ticket_id=ticket_id, user_id=current_user.id, content=comment_form.content.data)
                db.session.add(comment)
                db.session.commit()
                flash('Comment added successfully.', 'success')
            else:
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('admin_dashboard'))

    tickets_with_user = []
    for t in tickets:
        user = User.query.get(t.user_id) if t.user_id else None
        category = Category.query.get(t.category_id)
        tickets_with_user.append((t, user.username if user else "Unassigned", category.name if category else "Unknown"))

    comment_form = CommentForm()
    return render_template('admin_dashboard.html', tickets=tickets_with_user, categories=categories,
                           selected_category=category_id, comment_form=comment_form)

# Admin create ticket (separate from dashboard)
@app.route('/admin/create_ticket', methods=['GET', 'POST'])
@login_required
def admin_create_ticket():
    if current_user.role != 'Admin':
        abort(403)

    categories = Category.query.all()
    form = TicketForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        new_ticket = Ticket(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            created_at=datetime.utcnow(),
            user_id=current_user.id,
            category_id=form.category_id.data,
            created_by='admin'
        )
        db.session.add(new_ticket)
        db.session.commit()
        flash('Admin ticket created successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_create_ticket.html', form=form, categories=categories)

# User dashboard route - show tickets created by user with same interface as admin dashboard (no create ticket here)
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if current_user.role != 'User':
        abort(403)

    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    # Only tickets created by current user
    if category_id:
        tickets = Ticket.query.filter_by(user_id=current_user.id, category_id=category_id).all()
    else:
        tickets = Ticket.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            if ticket.user_id != current_user.id:
                abort(403)

            title            = (request.form.get('title') or '').strip()
            description      = (request.form.get('description') or '').strip()
            category_id_form = request.form.get('category_id', type=int)
            # Users are not permitted to change ticket status — ignored silently.

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
                db.session.commit()
                flash('Ticket updated successfully.', 'success')
            else:
                flash('No fields were provided to update.', 'warning')

            return redirect(url_for('user_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            if ticket.user_id != current_user.id:
                abort(403)

            db.session.delete(ticket)
            db.session.commit()
            flash('Ticket deleted successfully.', 'success')
            return redirect(url_for('user_dashboard'))

        elif action == 'add_comment':
            ticket_id = request.form.get('ticket_id', type=int)

            if ticket_id is None:
                flash('Ticket ID is missing.', 'danger')
                return redirect(url_for('user_dashboard'))

            ticket = Ticket.query.get(ticket_id)
            if not ticket or ticket.user_id != current_user.id:
                flash('Ticket not found or unauthorized.', 'danger')
                return redirect(url_for('user_dashboard'))

            comment_form = CommentForm()
            if comment_form.validate():
                comment = Comment(ticket_id=ticket_id, user_id=current_user.id, content=comment_form.content.data)
                db.session.add(comment)
                db.session.commit()
                flash('Comment added successfully.', 'success')
            else:
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('user_dashboard'))

    comment_form = CommentForm()
    return render_template('user_dashboard.html', tickets=tickets, categories=categories,
                           selected_category=category_id, comment_form=comment_form)

# User create ticket (separate from dashboard)
@app.route('/user/create_ticket', methods=['GET', 'POST'])
@login_required
def user_create_ticket():
    if current_user.role != 'User':
        abort(403)

    categories = Category.query.all()
    form = TicketForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        new_ticket = Ticket(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            created_at=datetime.utcnow(),
            user_id=current_user.id,
            category_id=form.category_id.data,
            created_by='user'
        )
        db.session.add(new_ticket)
        db.session.commit()
        flash('Ticket created successfully.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('user_create_ticket.html', form=form, categories=categories)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
