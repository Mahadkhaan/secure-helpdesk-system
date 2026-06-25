from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from models import Ticket, Comment, Category, User, db
from forms import TicketForm, CommentForm, VALID_STATUS_VALUES
from utils.security import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dashboard():
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
                    current_app.logger.warning(
                        '[VALIDATION] Invalid title length: len=%d user=%s ticket=%d',
                        len(title), current_user.username, ticket_id
                    )
                    flash('Title must be between 3 and 100 characters.', 'danger')
                    return redirect(url_for('admin.admin_dashboard'))
                ticket.title = title
                updated = True
            if description:
                if len(description) < 10:
                    current_app.logger.warning(
                        '[VALIDATION] Description too short: len=%d user=%s ticket=%d',
                        len(description), current_user.username, ticket_id
                    )
                    flash('Description must be at least 10 characters.', 'danger')
                    return redirect(url_for('admin.admin_dashboard'))
                ticket.description = description
                updated = True
            if status:
                if status not in VALID_STATUS_VALUES:
                    current_app.logger.warning(
                        '[VALIDATION] Invalid status value: status=%r user=%s ticket=%d',
                        status, current_user.username, ticket_id
                    )
                    flash('Invalid status value.', 'danger')
                    return redirect(url_for('admin.admin_dashboard'))
                ticket.status = status
                updated = True
            if category_id_form is not None:
                ticket.category_id = category_id_form
                updated = True

            if updated:
                try:
                    db.session.commit()
                    current_app.logger.info(
                        '[TICKET] Admin updated ticket: ticket_id=%d admin=%s',
                        ticket_id, current_user.username
                    )
                    flash('Ticket updated successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    current_app.logger.error(
                        '[DB] Error updating ticket %d', ticket_id, exc_info=True
                    )
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                flash('No fields were provided to update.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)
            try:
                db.session.delete(ticket)
                db.session.commit()
                current_app.logger.warning(
                    '[TICKET] Admin deleted ticket: ticket_id=%d admin=%s',
                    ticket_id, current_user.username
                )
                flash('Ticket deleted successfully.', 'success')
            except Exception:
                db.session.rollback()
                current_app.logger.error(
                    '[DB] Error deleting ticket %d', ticket_id, exc_info=True
                )
                flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('admin.admin_dashboard'))

        elif action == 'add_comment':
            ticket_id = request.form.get('ticket_id', type=int)
            if ticket_id is None:
                flash('Ticket ID is missing.', 'danger')
                return redirect(url_for('admin.admin_dashboard'))

            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                flash('Ticket not found.', 'danger')
                return redirect(url_for('admin.admin_dashboard'))

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
                    current_app.logger.info(
                        '[TICKET] Admin added comment: ticket_id=%d admin=%s',
                        ticket_id, current_user.username
                    )
                    flash('Comment added successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    current_app.logger.error(
                        '[DB] Error adding comment to ticket %d', ticket_id, exc_info=True
                    )
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                current_app.logger.warning(
                    '[VALIDATION] Invalid comment: user=%s ticket=%d',
                    current_user.username, ticket_id
                )
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('admin.admin_dashboard'))

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


@admin_bp.route('/admin/create_ticket', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_ticket():
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
            current_app.logger.info(
                '[TICKET] Admin created ticket: ticket_id=%d title=%r admin=%s',
                new_ticket.id, new_ticket.title, current_user.username
            )
            flash('Admin ticket created successfully.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception:
            db.session.rollback()
            current_app.logger.error(
                '[DB] Error creating ticket for admin=%s',
                current_user.username, exc_info=True
            )
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('admin_create_ticket.html', form=form, categories=categories)
