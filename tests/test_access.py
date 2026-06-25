"""Access-control tests: who can reach which routes."""
from models import db as _db, Ticket


# ── Unauthenticated redirects ──────────────────────────────────────────────────

def test_unauthenticated_redirected_from_user_dashboard(client):
    response = client.get('/user/dashboard')
    # login_manager redirects unauthenticated requests to login_view (main.home)
    assert response.status_code == 302


def test_unauthenticated_redirected_from_admin_dashboard(client):
    response = client.get('/admin/dashboard')
    assert response.status_code == 302


def test_unauthenticated_cannot_create_ticket(client):
    response = client.get('/user/create_ticket')
    assert response.status_code == 302


# ── Role-based access ──────────────────────────────────────────────────────────

def test_user_blocked_from_admin_dashboard(user_client):
    response = user_client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b'Access Denied' in response.data


def test_user_blocked_from_admin_create_ticket(user_client):
    response = user_client.get('/admin/create_ticket')
    assert response.status_code == 403


def test_admin_blocked_from_user_dashboard(admin_client):
    response = admin_client.get('/user/dashboard')
    assert response.status_code == 403
    assert b'Access Denied' in response.data


# ── Cross-user ticket access ───────────────────────────────────────────────────

def test_user_cannot_update_others_ticket(app, user_client, other_ticket_id):
    response = user_client.post('/user/dashboard', data={
        'action': 'update',
        'ticket_id': other_ticket_id,
        'title': 'Injected Title',
    }, follow_redirects=True)
    assert response.status_code == 403


def test_user_cannot_delete_others_ticket(app, user_client, other_ticket_id):
    response = user_client.post('/user/dashboard', data={
        'action': 'delete',
        'ticket_id': other_ticket_id,
    }, follow_redirects=True)
    assert response.status_code == 403
    # Confirm the ticket was not actually deleted.
    with app.app_context():
        assert Ticket.query.get(other_ticket_id) is not None
