from models import db, Category
from app import app


default_categories = ['Software', 'Hardware', 'Network', 'Account', 'Other']

with app.app_context():
    for cat_name in default_categories:
        existing_cat = Category.query.filter_by(name=cat_name).first()
        if not existing_cat:
            new_cat = Category(name=cat_name)
            db.session.add(new_cat)
    db.session.commit()
    print("Default categories added (if not present).")
