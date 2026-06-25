from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import current_user, login_required
from models import Ticket, Comment, Category, db
from forms import TicketForm, CommentForm
from utils.security import user_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
@user_required
def user_dashboard():
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
                current_app.logger.warning(
                    "[SECURITY] User attempted to update another user's ticket: "
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
                    return redirect(url_for('user.user_dashboard'))
                ticket.title = title
                updated = True
            if description:
                if len(description) < 10:
                    flash('Description must be at least 10 characters.', 'danger')
                    return redirect(url_for('user.user_dashboard'))
                ticket.description = description
                updated = True
            if category_id_form is not None:
                ticket.category_id = category_id_form
                updated = True

            if updated:
                try:
                    db.session.commit()
                    current_app.logger.info(
                        '[TICKET] User updated ticket: ticket_id=%d user=%s',
                        ticket_id, current_user.username
                    )
                    flash('Ticket updated successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    current_app.logger.error(
                        '[DB] Error updating ticket %d for user=%s',
                        ticket_id, current_user.username, exc_info=True
                    )
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                flash('No fields were provided to update.', 'warning')
            return redirect(url_for('user.user_dashboard'))

        elif action == 'delete':
            ticket_id = request.form.get('ticket_id', type=int)
            ticket = Ticket.query.get_or_404(ticket_id)

            if ticket.user_id != current_user.id:
                current_app.logger.warning(
                    "[SECURITY] User attempted to delete another user's ticket: "
                    'user=%s ticket_id=%d owner_id=%d ip=%s',
                    current_user.username, ticket_id, ticket.user_id, request.remote_addr
                )
                abort(403)

            try:
                db.session.delete(ticket)
                db.session.commit()
                current_app.logger.warning(
                    '[TICKET] User deleted ticket: ticket_id=%d user=%s',
                    ticket_id, current_user.username
                )
                flash('Ticket deleted successfully.', 'success')
            except Exception:
                db.session.rollback()
                current_app.logger.error(
                    '[DB] Error deleting ticket %d for user=%s',
                    ticket_id, current_user.username, exc_info=True
                )
                flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('user.user_dashboard'))

        elif action == 'add_comment':
            ticket_id = request.form.get('ticket_id', type=int)
            if ticket_id is None:
                flash('Ticket ID is missing.', 'danger')
                return redirect(url_for('user.user_dashboard'))

            ticket = Ticket.query.get(ticket_id)
            if not ticket or ticket.user_id != current_user.id:
                current_app.logger.warning(
                    '[SECURITY] User attempted to comment on unauthorized ticket: '
                    'user=%s ticket_id=%s ip=%s',
                    current_user.username, ticket_id, request.remote_addr
                )
                flash('Ticket not found or unauthorized.', 'danger')
                return redirect(url_for('user.user_dashboard'))

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
                        '[TICKET] User added comment: ticket_id=%d user=%s',
                        ticket_id, current_user.username
                    )
                    flash('Comment added successfully.', 'success')
                except Exception:
                    db.session.rollback()
                    current_app.logger.error(
                        '[DB] Error adding comment to ticket %d for user=%s',
                        ticket_id, current_user.username, exc_info=True
                    )
                    flash('An unexpected error occurred. Please try again.', 'danger')
            else:
                current_app.logger.warning(
                    '[VALIDATION] Invalid comment: user=%s ticket=%d',
                    current_user.username, ticket_id
                )
                flash('Comment must be between 1 and 1000 characters.', 'danger')
            return redirect(url_for('user.user_dashboard'))

    comment_form = CommentForm()
    return render_template(
        'user_dashboard.html',
        tickets=tickets,
        categories=categories,
        selected_category=category_id,
        comment_form=comment_form
    )


@user_bp.route('/user/create_ticket', methods=['GET', 'POST'])
@login_required
@user_required
def user_create_ticket():
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
            current_app.logger.info(
                '[TICKET] User created ticket: ticket_id=%d title=%r user=%s',
                new_ticket.id, new_ticket.title, current_user.username
            )
            flash('Ticket created successfully.', 'success')
            return redirect(url_for('user.user_dashboard'))
        except Exception:
            db.session.rollback()
            current_app.logger.error(
                '[DB] Error creating ticket for user=%s',
                current_user.username, exc_info=True
            )
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('user_create_ticket.html', form=form, categories=categories)
