"""Startup initialisation tests: schema creation and category seeding."""
from models import Category
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
