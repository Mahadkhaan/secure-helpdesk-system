"""Error handler and security-boundary tests."""
import pytest


# ── HTTP error pages ───────────────────────────────────────────────────────────

def test_404_returns_error_page(client):
    response = client.get('/this-route-does-not-exist')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data


def test_403_page_rendered_for_unauthorized_user(user_client):
    response = user_client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b'Access Denied' in response.data


# ── CSRF protection ────────────────────────────────────────────────────────────

def test_csrf_protection_returns_400(csrf_client):
    # POST with no CSRF token to any form endpoint should return 400.
    response = csrf_client.post('/login/user', data={
        'username': 'testuser',
        'password': 'TestPass1!',
    })
    assert response.status_code == 400
    assert b'Bad Request' in response.data


# ── Admin registration code enforcement ───────────────────────────────────────

def test_admin_register_code_not_configured(app):
    """When ADMIN_REGISTRATION_CODE is empty, the endpoint is disabled."""
    from config import Config
    from app import create_app
    from sqlalchemy.pool import StaticPool

    class NoCodeConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        }
        WTF_CSRF_ENABLED = False
        SECRET_KEY = 'test-key'
        ADMIN_REGISTRATION_CODE = ''  # disabled

    application = create_app(NoCodeConfig)
    from models import db as _db
    with application.app_context():
        _db.create_all()
        client = application.test_client()
        response = client.post('/register/admin', data={
            'username': 'hacker',
            'email': 'hacker@example.com',
            'password': 'HackerPass1!',
            'registration_code': '',
        }, follow_redirects=True)
        # The route redirects to home.html. home.html has no flash block, so we
        # confirm we landed on the home page rather than the registration form.
        assert b'Support Ticket System' in response.data
        assert b'Admin Registration' not in response.data
        _db.drop_all()
