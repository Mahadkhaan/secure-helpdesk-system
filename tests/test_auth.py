"""Authentication tests: registration, login, logout."""


# ── User registration ──────────────────────────────────────────────────────────

def test_user_register_success(client):
    response = client.post('/register/user', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'StrongPass1!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User Login' in response.data


def test_user_register_duplicate_email(client, user_id):
    response = client.post('/register/user', data={
        'username': 'differentname',
        'email': 'user@test.com',  # same email as user_id fixture
        'password': 'StrongPass1!',
    }, follow_redirects=True)
    assert b'Email already registered' in response.data


def test_user_register_duplicate_username(client, user_id):
    response = client.post('/register/user', data={
        'username': 'testuser',  # same username as user_id fixture
        'email': 'different@example.com',
        'password': 'StrongPass1!',
    }, follow_redirects=True)
    assert b'Username already taken' in response.data


# ── User login ─────────────────────────────────────────────────────────────────

def test_user_login_success(client, user_id):
    response = client.post('/login/user', data={
        'username': 'testuser',
        'password': 'TestPass1!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User Dashboard' in response.data


def test_user_login_wrong_password(client, user_id):
    response = client.post('/login/user', data={
        'username': 'testuser',
        'password': 'WrongPassword1!',
    }, follow_redirects=True)
    assert b'Invalid user credentials' in response.data


def test_user_login_wrong_role(client, admin_id):
    # Admin account cannot log in via the user login endpoint.
    response = client.post('/login/user', data={
        'username': 'adminuser',
        'password': 'AdminPass1!',
    }, follow_redirects=True)
    assert b'Invalid user credentials' in response.data


# ── Admin registration ─────────────────────────────────────────────────────────

def test_admin_register_success(client):
    response = client.post('/register/admin', data={
        'username': 'newadmin',
        'email': 'newadmin@example.com',
        'password': 'AdminPass1!',
        'registration_code': 'test-admin-code',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Login' in response.data


def test_admin_register_wrong_code(client):
    response = client.post('/register/admin', data={
        'username': 'newadmin',
        'email': 'newadmin@example.com',
        'password': 'AdminPass1!',
        'registration_code': 'wrong-code',
    }, follow_redirects=True)
    assert b'Invalid registration code' in response.data


# ── Admin login ────────────────────────────────────────────────────────────────

def test_admin_login_success(client, admin_id):
    response = client.post('/login/admin', data={
        'username': 'adminuser',
        'password': 'AdminPass1!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data


def test_admin_login_wrong_password(client, admin_id):
    response = client.post('/login/admin', data={
        'username': 'adminuser',
        'password': 'WrongPassword1!',
    }, follow_redirects=True)
    assert b'Invalid admin credentials' in response.data


# ── Logout ─────────────────────────────────────────────────────────────────────

def test_logout(user_client):
    response = user_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    # home.html is rendered after logout (no flash block there, but the
    # page title confirms we reached the home page).
    assert b'Support Ticket System' in response.data
    # Confirm session is cleared: protected route now redirects away.
    response2 = user_client.get('/user/dashboard', follow_redirects=True)
    assert b'User Dashboard' not in response2.data
