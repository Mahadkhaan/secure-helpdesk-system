import os


class Config:
    # Set these in .env locally (see .env.example); never rely on the defaults in production.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-before-deploying')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///support.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session hardening
    SESSION_COOKIE_HTTPONLY = True          # JS cannot read the session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'        # CSRF mitigation for cross-site requests
    # Set SESSION_COOKIE_SECURE=true in production (HTTPS only)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

    # Admin self-registration gate. If empty, /register/admin is completely disabled.
    ADMIN_REGISTRATION_CODE = os.environ.get('ADMIN_REGISTRATION_CODE', '')
