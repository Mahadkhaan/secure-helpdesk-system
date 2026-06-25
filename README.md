# Helpdesk Ticket System

A web-based support ticket management system built with Flask. Users can create and track support tickets; admins can triage, update, and close them.

---

## Features

- **Role-based accounts** — separate Admin and User roles with distinct dashboards
- **Ticket management** — create, update, delete, and comment on tickets
- **Category filtering** — filter tickets by category on both dashboards
- **Status workflow** — Open → In Progress → Closed (admin-controlled)
- **CSRF protection** — every form is protected by Flask-WTF globally
- **Input validation** — server-side validation on all forms with inline error messages
- **Structured logging** — rotating log files with security-event tagging
- **Custom error pages** — Bootstrap-styled 400 / 403 / 404 / 500 pages
- **Modular structure** — Flask Blueprints for auth, admin, user, and main routes
- **Automated tests** — 40 pytest tests covering auth, access control, CRUD, validation, and security
- **CI pipeline** — GitHub Actions runs the full test suite on every push and PR
- **Docker support** — production container using Gunicorn

---

## Security Features

| OWASP Category | Implementation |
|---|---|
| A01 Broken Access Control | `@admin_required` / `@user_required` decorators on every protected route; ownership check before any cross-user ticket operation |
| A02 Cryptographic Failures | Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2-HMAC-SHA256); never stored or logged in plain text |
| A05 Security Misconfiguration | All config loaded from environment variables via `config.py`; `debug=False` in production; `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE=Lax`; HTTPS-only session cookies configurable via `SESSION_COOKIE_SECURE` |
| A07 Identification and Authentication Failures | Minimum 8-character password with uppercase, lowercase, digit, and special character enforced by a WTForms validator; admin registration gated behind `ADMIN_REGISTRATION_CODE`; failed login attempts logged with IP |
| CSRF | `CSRFProtect(app)` applied globally — every POST without a valid token returns 400 |

---

## Project Structure

```
ticket-main/
├── app.py                  # Application factory (create_app)
├── config.py               # Config loaded from environment variables
├── models.py               # SQLAlchemy models (User, Ticket, Comment, Category)
├── forms.py                # WTForms form classes and validators
├── routes/
│   ├── main.py             # Home, choose_role, dashboard redirect
│   ├── auth.py             # Login, register, logout (admin + user)
│   ├── admin.py            # Admin dashboard and ticket management
│   └── user.py             # User dashboard and ticket management
├── utils/
│   ├── logging_config.py   # Rotating file + console logging setup
│   └── security.py         # @admin_required / @user_required decorators
├── templates/              # Jinja2 HTML templates (Bootstrap 5)
├── tests/
│   ├── conftest.py         # Pytest fixtures and TestingConfig
│   ├── test_auth.py        # Authentication tests
│   ├── test_access.py      # Access-control tests
│   ├── test_tickets.py     # CRUD tests
│   ├── test_validation.py  # Input validation tests
│   └── test_errors.py      # Error handler and security-boundary tests
├── migrations/             # Flask-Migrate (Alembic) migration scripts
├── logs/                   # Runtime log files (git-ignored, directory tracked)
├── .github/workflows/
│   └── tests.yml           # GitHub Actions CI
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Prerequisites

- Python 3.10 or later
- pip
- Git

---

## Local Setup (without Docker)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ticket-main
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY` and an `ADMIN_REGISTRATION_CODE`. See the [Environment Variables](#environment-variables) section below.

### 5. Initialise the database

```bash
flask db upgrade
```

### 6. Seed categories (first run only)

```bash
python init_categories.py
```

### 7. Start the development server

```bash
python app.py
```

The app is now running at `http://127.0.0.1:5000`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values. Never commit `.env` to version control.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | `change-me-before-deploying` | Flask session signing key. Use a long random string (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | No | `sqlite:///support.db` | SQLAlchemy connection string. Use a PostgreSQL URL in production |
| `ADMIN_REGISTRATION_CODE` | Recommended | *(empty — disabled)* | Secret code required to register an admin account. Leave empty to block admin self-registration entirely |
| `SESSION_COOKIE_SECURE` | Prod only | `false` | Set to `true` when serving over HTTPS to prevent session cookies being sent over plain HTTP |
| `FLASK_DEBUG` | No | `0` | Set to `1` for Werkzeug debugger in development. **Never set to 1 in production** |

---

## Running Tests

Tests use an isolated in-memory SQLite database and never touch your `.env` file or production database.

```bash
# Run all 40 tests
pytest

# Verbose output (shows each test name)
pytest -v

# With coverage report
pytest --cov=. --cov-report=term-missing

# Run a single test file
pytest tests/test_auth.py -v
```

### What is tested

| File | Tests | Coverage |
|---|---|---|
| `test_auth.py` | User/admin registration, login, wrong credentials, wrong role, logout | Auth routes, form validators |
| `test_access.py` | Unauthenticated redirects, role blocks (403), cross-user ticket attacks | `@admin_required`, `@user_required`, ownership checks |
| `test_tickets.py` | Create, update, delete, comment for both roles; status-change ignored for users | CRUD routes, DB writes |
| `test_validation.py` | Invalid email, weak passwords (4 variants), short title/description, invalid status | WTForms validators, server-side whitelist |
| `test_errors.py` | 404 page, 403 page, CSRF rejection (400), admin registration disabled | Error handlers, `CSRFProtect` |

---

## CI with GitHub Actions

The workflow at `.github/workflows/tests.yml` runs automatically on every push and pull request.

**What it does:**

1. Checks out the repository
2. Sets up Python 3.12 with pip caching
3. Installs all dependencies from `requirements.txt`
4. Runs `pytest --cov=. --cov-report=term-missing --cov-report=xml`
5. Uploads `coverage.xml` as a downloadable artifact (retained for 7 days)

**Environment variables in CI** are safe dummy values. `TestingConfig` (in `tests/conftest.py`) overrides all of them for the actual test run, so no real secrets are needed.

**Viewing results:** Go to your GitHub repository → **Actions** tab → click the latest run → expand "Run pytest with coverage" to see all 40 test results and the coverage table.

---

## Docker

### Build the image

```bash
docker build -t helpdesk-app .
```

### Run the container

```bash
docker run -d \
  --name helpdesk \
  -p 8000:8000 \
  -e SECRET_KEY="your-long-random-secret-key" \
  -e ADMIN_REGISTRATION_CODE="your-admin-code" \
  -e DATABASE_URL="sqlite:////app/instance/support.db" \
  -v helpdesk-data:/app/instance \
  helpdesk-app
```

The app is now running at `http://localhost:8000`.

| Flag | Purpose |
|---|---|
| `-e SECRET_KEY=...` | Required — Flask session signing key |
| `-e ADMIN_REGISTRATION_CODE=...` | Code to gate admin self-registration |
| `-e DATABASE_URL=sqlite:////app/instance/support.db` | Stores the database inside the mounted volume |
| `-v helpdesk-data:/app/instance` | Named volume so the database survives container restarts |

### Initialise the database (first run)

```bash
docker exec helpdesk flask db upgrade
```

### View logs

```bash
docker logs -f helpdesk
```

### Stop and remove

```bash
docker stop helpdesk && docker rm helpdesk
```

---

## Deployment

### Render (recommended for quick deployment)

Render can deploy directly from a Dockerfile.

1. Push this repository to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect your GitHub repository.
4. Set **Environment** to `Docker`.
5. Set **Port** to `8000`.
6. Under **Environment Variables**, add:
   - `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
   - `ADMIN_REGISTRATION_CODE` — a secret string you choose
   - `DATABASE_URL` — use a PostgreSQL URL (Render provides managed PostgreSQL on the free tier); see note below
   - `SESSION_COOKIE_SECURE` — `true` (Render serves over HTTPS)
7. Click **Deploy**.
8. After deployment, open the Render shell and run `flask db upgrade` to initialise the database.

### Important production settings

| Setting | Value | Why |
|---|---|---|
| `SECRET_KEY` | Long random string | Prevents session forgery |
| `SESSION_COOKIE_SECURE` | `true` | Ensures cookies are only sent over HTTPS |
| `FLASK_DEBUG` | `0` (or unset) | Prevents the debugger PIN from being exposed |
| `ADMIN_REGISTRATION_CODE` | A secret string | Controls who can create admin accounts |
| Database | PostgreSQL (not SQLite) | SQLite is single-file; not suitable for multi-worker or multi-instance deployments |

### SQLite vs PostgreSQL

This app defaults to SQLite, which is fine for local development and single-instance Docker deployments with one or two Gunicorn workers. For production on Render or any platform with multiple workers or auto-scaling, switch to PostgreSQL:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Install the driver:

```bash
pip install psycopg2-binary
```

No application code changes are needed — SQLAlchemy handles the dialect automatically.
