from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from forms import AdminLoginForm, UserLoginForm, AdminRegisterForm, UserRegisterForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='Admin').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            current_app.logger.info(
                '[AUTH] Admin login success: user=%s ip=%s',
                user.username, request.remote_addr
            )
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        current_app.logger.warning(
            '[AUTH] Admin login failure: attempted_user=%s ip=%s',
            form.username.data, request.remote_addr
        )
        flash('Invalid admin credentials.', 'danger')
    return render_template('login_admin.html', form=form)


@auth_bp.route('/register/admin', methods=['GET', 'POST'])
def admin_register():
    reg_code = current_app.config.get('ADMIN_REGISTRATION_CODE', '')
    if not reg_code:
        current_app.logger.warning(
            '[AUTH] Admin registration attempted but disabled: ip=%s',
            request.remote_addr
        )
        flash('Admin registration is disabled. Contact an existing administrator.', 'danger')
        return redirect(url_for('main.home'))

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = AdminRegisterForm()
    if form.validate_on_submit():
        if form.registration_code.data != reg_code:
            current_app.logger.warning(
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
            current_app.logger.info(
                '[AUTH] Admin registered: user=%s ip=%s',
                new_user.username, request.remote_addr
            )
            flash('Admin registration successful. Please login.', 'success')
            return redirect(url_for('auth.admin_login'))
        except Exception:
            db.session.rollback()
            current_app.logger.error(
                '[DB] Admin registration DB error: user=%s',
                form.username.data, exc_info=True
            )
            flash('An unexpected error occurred. Please try again.', 'danger')
    return render_template('register_admin.html', form=form)


@auth_bp.route('/login/user', methods=['GET', 'POST'])
def user_login():
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, role='User').first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            current_app.logger.info(
                '[AUTH] User login success: user=%s ip=%s',
                user.username, request.remote_addr
            )
            flash('User login successful.', 'success')
            return redirect(url_for('user.user_dashboard'))
        current_app.logger.warning(
            '[AUTH] User login failure: attempted_user=%s ip=%s',
            form.username.data, request.remote_addr
        )
        flash('Invalid user credentials.', 'danger')
    return render_template('login_user.html', form=form)


@auth_bp.route('/register/user', methods=['GET', 'POST'])
def user_register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
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
            current_app.logger.info(
                '[AUTH] User registered: user=%s ip=%s',
                new_user.username, request.remote_addr
            )
            flash('User registration successful. Please login.', 'success')
            return redirect(url_for('auth.user_login'))
        except Exception:
            db.session.rollback()
            current_app.logger.error(
                '[DB] User registration DB error: user=%s',
                form.username.data, exc_info=True
            )
            flash('An unexpected error occurred. Please try again.', 'danger')
    return render_template('register_user.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info(
        '[AUTH] Logout: user=%s role=%s ip=%s',
        current_user.username, current_user.role, request.remote_addr
    )
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))
