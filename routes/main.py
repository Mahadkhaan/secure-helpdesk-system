from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('user.user_dashboard'))
    return render_template('home.html')


@main_bp.route('/choose_role/<action>')
def choose_role(action):
    if action not in ['login', 'register']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('main.home'))
    return render_template(
        'choose_role.html',
        action=action,
        admin_endpoint=f'auth.admin_{action}',
        user_endpoint=f'auth.user_{action}'
    )


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('user.user_dashboard'))
