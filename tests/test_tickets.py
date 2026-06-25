"""CRUD tests for ticket and comment operations."""
from models import db as _db, Ticket


# ── User: create ───────────────────────────────────────────────────────────────

def test_user_create_ticket(app, user_client, category_id):
    response = user_client.post('/user/create_ticket', data={
        'title': 'My New Ticket',
        'description': 'Detailed description of the issue I am facing.',
        'status': 'Open',
        'category_id': category_id,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Ticket created successfully' in response.data
    with app.app_context():
        assert Ticket.query.filter_by(title='My New Ticket').first() is not None


# ── User: update own ticket ────────────────────────────────────────────────────

def test_user_update_own_ticket(app, user_client, ticket_id):
    response = user_client.post('/user/dashboard', data={
        'action': 'update',
        'ticket_id': ticket_id,
        'title': 'Updated Title',
        'description': 'Updated description that is long enough.',
        'category_id': 1,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Ticket updated successfully' in response.data
    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        assert ticket.title == 'Updated Title'


def test_user_status_change_is_ignored(app, user_client, ticket_id):
    # Users submit a status field but the route silently ignores it.
    user_client.post('/user/dashboard', data={
        'action': 'update',
        'ticket_id': ticket_id,
        'status': 'Closed',
        'title': 'Some Title',
        'category_id': 1,
    }, follow_redirects=True)
    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        assert ticket.status == 'Open'  # Status unchanged


# ── User: delete own ticket ────────────────────────────────────────────────────

def test_user_delete_own_ticket(app, user_client, ticket_id):
    response = user_client.post('/user/dashboard', data={
        'action': 'delete',
        'ticket_id': ticket_id,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Ticket deleted successfully' in response.data
    with app.app_context():
        assert Ticket.query.get(ticket_id) is None


# ── User: add comment ──────────────────────────────────────────────────────────

def test_user_add_comment(user_client, ticket_id):
    response = user_client.post('/user/dashboard', data={
        'action': 'add_comment',
        'ticket_id': ticket_id,
        'content': 'This is my comment on the ticket.',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Comment added successfully' in response.data


# ── Admin: create ──────────────────────────────────────────────────────────────

def test_admin_create_ticket(app, admin_client, category_id):
    response = admin_client.post('/admin/create_ticket', data={
        'title': 'Admin Created Ticket',
        'description': 'This ticket was created by an administrator.',
        'status': 'Open',
        'category_id': category_id,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin ticket created successfully' in response.data
    with app.app_context():
        assert Ticket.query.filter_by(title='Admin Created Ticket').first() is not None


# ── Admin: update status ───────────────────────────────────────────────────────

def test_admin_update_ticket_status(app, admin_client, ticket_id):
    response = admin_client.post('/admin/dashboard', data={
        'action': 'update',
        'ticket_id': ticket_id,
        'status': 'Closed',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Ticket updated successfully' in response.data
    with app.app_context():
        assert Ticket.query.get(ticket_id).status == 'Closed'


# ── Admin: delete ──────────────────────────────────────────────────────────────

def test_admin_delete_ticket(app, admin_client, ticket_id):
    response = admin_client.post('/admin/dashboard', data={
        'action': 'delete',
        'ticket_id': ticket_id,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Ticket deleted successfully' in response.data
    with app.app_context():
        assert Ticket.query.get(ticket_id) is None


# ── Admin: add comment ─────────────────────────────────────────────────────────

def test_admin_add_comment(admin_client, ticket_id):
    response = admin_client.post('/admin/dashboard', data={
        'action': 'add_comment',
        'ticket_id': ticket_id,
        'content': 'Admin remark on this ticket.',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Comment added successfully' in response.data
