"""Startup initialisation tests: schema creation, category seeding, and demo data."""
from models import Category, User, Ticket, Comment
from app import DEFAULT_CATEGORIES, _seed_default_categories


def test_default_categories_seeded(app):
    """All five default categories should exist after create_app()."""
    names = {c.name for c in Category.query.all()}
    for expected in DEFAULT_CATEGORIES:
        assert expected in names


def test_seeding_is_idempotent(app):
    """Calling _seed_default_categories() again must not duplicate rows."""
    count_before = Category.query.count()
    _seed_default_categories()
    assert Category.query.count() == count_before


# ── flask seed-demo-data ───────────────────────────────────────────────────────

def test_seed_demo_data_creates_expected_records(app):
    """seed-demo-data should create 3 users, 4 tickets, and 3 comments."""
    result = app.test_cli_runner().invoke(args=['seed-demo-data'])
    assert result.exit_code == 0
    assert 'Demo data seeded:' in result.output
    assert 'Generated credentials' in result.output

    usernames = {u.username for u in User.query.filter(User.username.like('demo_%')).all()}
    assert usernames == {'demo_admin', 'demo_user1', 'demo_user2'}

    demo_tickets = Ticket.query.filter(Ticket.title.like('[DEMO]%')).all()
    assert len(demo_tickets) == 4

    admin_id = User.query.filter_by(username='demo_admin').first().id
    demo_comments = Comment.query.filter_by(user_id=admin_id).all()
    assert len(demo_comments) == 3


def test_seed_demo_data_is_idempotent(app):
    """Running seed-demo-data twice must not duplicate any records."""
    runner = app.test_cli_runner()
    runner.invoke(args=['seed-demo-data'])
    result = runner.invoke(args=['seed-demo-data'])

    assert result.exit_code == 0
    assert 'nothing changed' in result.output
    assert User.query.filter(User.username.like('demo_%')).count() == 3
    assert Ticket.query.filter(Ticket.title.like('[DEMO]%')).count() == 4


def test_seed_demo_data_partial_recovery_creates_missing_ticket(app):
    """Deleting one demo ticket and re-running must recreate only that ticket."""
    runner = app.test_cli_runner()
    runner.invoke(args=['seed-demo-data'])

    target = Ticket.query.filter_by(title='[DEMO] VPN drops after 10 minutes').first()
    assert target is not None
    Comment.query.filter_by(ticket_id=target.id).delete()
    Ticket.query.filter_by(id=target.id).delete()
    from models import db
    db.session.commit()

    assert Ticket.query.filter(Ticket.title.like('[DEMO]%')).count() == 3

    result = runner.invoke(args=['seed-demo-data'])
    assert result.exit_code == 0
    assert Ticket.query.filter(Ticket.title.like('[DEMO]%')).count() == 4
    assert 'nothing changed' not in result.output


def test_seed_demo_data_passwords_are_hashed(app):
    """Demo user passwords must be stored as hashes, never as plaintext."""
    app.test_cli_runner().invoke(args=['seed-demo-data'])

    for username in ('demo_admin', 'demo_user1', 'demo_user2'):
        user = User.query.filter_by(username=username).first()
        assert user is not None
        # Werkzeug hashes are long (>30 chars) and contain colons (method:salt:hash).
        assert len(user.password) > 30
        assert ':' in user.password
        # Raw passwords must not appear anywhere in the stored hash.
        for raw in ('DemoAdmin1!', 'DemoUser1!', 'DemoUser2!'):
            assert raw not in user.password
