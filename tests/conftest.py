import pytest
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from models import db as _db, User, Category, Ticket


class TestingConfig(Config):
    TESTING = True
    # StaticPool ensures all connections share the same in-memory SQLite database,
    # so data written in fixtures is visible to requests made through the test client.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
        'poolclass': StaticPool,
    }
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'testing-secret-key'
    ADMIN_REGISTRATION_CODE = 'test-admin-code'


class CSRFConfig(TestingConfig):
    WTF_CSRF_ENABLED = True


# ── App / client ───────────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
        _db.session.add(Category(name='General'))
        _db.session.commit()
        yield application
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf_client():
    """Separate client with CSRF enforcement enabled, for CSRF rejection tests."""
    application = create_app(CSRFConfig)
    with application.app_context():
        _db.create_all()
        yield application.test_client()
        _db.drop_all()


# ── Database helpers ───────────────────────────────────────────────────────────

@pytest.fixture()
def category_id(app):
    return Category.query.first().id


@pytest.fixture()
def user_id(app):
    u = User(
        username='testuser',
        email='user@test.com',
        password=generate_password_hash('TestPass1!'),
        role='User',
    )
    _db.session.add(u)
    _db.session.commit()
    return u.id


@pytest.fixture()
def second_user_id(app):
    u = User(
        username='otheruser',
        email='other@test.com',
        password=generate_password_hash('TestPass1!'),
        role='User',
    )
    _db.session.add(u)
    _db.session.commit()
    return u.id


@pytest.fixture()
def admin_id(app):
    a = User(
        username='adminuser',
        email='admin@test.com',
        password=generate_password_hash('AdminPass1!'),
        role='Admin',
    )
    _db.session.add(a)
    _db.session.commit()
    return a.id


@pytest.fixture()
def ticket_id(app, user_id, category_id):
    t = Ticket(
        title='Test Ticket',
        description='This is a sufficiently long description for the test ticket.',
        status='Open',
        user_id=user_id,
        category_id=category_id,
        created_by='user',
    )
    _db.session.add(t)
    _db.session.commit()
    return t.id


@pytest.fixture()
def other_ticket_id(app, second_user_id, category_id):
    """A ticket owned by the second (other) user."""
    t = Ticket(
        title='Other User Ticket',
        description='This ticket belongs to the second user, not testuser.',
        status='Open',
        user_id=second_user_id,
        category_id=category_id,
        created_by='user',
    )
    _db.session.add(t)
    _db.session.commit()
    return t.id


# ── Authenticated clients ──────────────────────────────────────────────────────

@pytest.fixture()
def user_client(client, user_id):
    r = client.post(
        '/login/user',
        data={'username': 'testuser', 'password': 'TestPass1!'},
        follow_redirects=True,
    )
    assert b'User Dashboard' in r.data, 'user_client login fixture failed'
    return client


@pytest.fixture()
def admin_client(client, admin_id):
    r = client.post(
        '/login/admin',
        data={'username': 'adminuser', 'password': 'AdminPass1!'},
        follow_redirects=True,
    )
    assert b'Admin Dashboard' in r.data, 'admin_client login fixture failed'
    return client
