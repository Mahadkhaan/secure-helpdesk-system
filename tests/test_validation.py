"""Input validation tests: email, password strength, field lengths, status whitelist."""


# ── Registration: email ────────────────────────────────────────────────────────

def test_register_invalid_email(client):
    response = client.post('/register/user', data={
        'username': 'baduser',
        'email': 'not-an-email',
        'password': 'StrongPass1!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User Register' in response.data or b'Invalid email' in response.data
    assert b'Registration successful' not in response.data


# ── Registration: password strength ───────────────────────────────────────────

def test_register_password_too_short(client):
    response = client.post('/register/user', data={
        'username': 'shortpass',
        'email': 'short@example.com',
        'password': 'Ab1!',  # Only 4 chars
    }, follow_redirects=True)
    assert b'Registration successful' not in response.data
    assert b'at least 8' in response.data


def test_register_password_no_uppercase(client):
    response = client.post('/register/user', data={
        'username': 'noupper',
        'email': 'noupper@example.com',
        'password': 'lowercase1!',
    }, follow_redirects=True)
    assert b'Registration successful' not in response.data
    assert b'uppercase' in response.data


def test_register_password_no_digit(client):
    response = client.post('/register/user', data={
        'username': 'nodigit',
        'email': 'nodigit@example.com',
        'password': 'NoDigitPass!',
    }, follow_redirects=True)
    assert b'Registration successful' not in response.data
    assert b'digit' in response.data


def test_register_password_no_special(client):
    response = client.post('/register/user', data={
        'username': 'nospecial',
        'email': 'nospecial@example.com',
        'password': 'NoSpecial123',
    }, follow_redirects=True)
    assert b'Registration successful' not in response.data
    assert b'special' in response.data


# ── Ticket creation: field lengths ────────────────────────────────────────────

def test_ticket_title_too_short(user_client, category_id):
    response = user_client.post('/user/create_ticket', data={
        'title': 'Hi',  # Only 2 chars, minimum is 3
        'description': 'A sufficiently long description for the ticket.',
        'status': 'Open',
        'category_id': category_id,
    }, follow_redirects=True)
    assert b'Ticket created successfully' not in response.data


def test_ticket_description_too_short(user_client, category_id):
    response = user_client.post('/user/create_ticket', data={
        'title': 'Valid Title',
        'description': 'Short',  # Only 5 chars, minimum is 10
        'status': 'Open',
        'category_id': category_id,
    }, follow_redirects=True)
    assert b'Ticket created successfully' not in response.data


# ── Admin: status whitelist ────────────────────────────────────────────────────

def test_admin_update_invalid_status(admin_client, ticket_id):
    response = admin_client.post('/admin/dashboard', data={
        'action': 'update',
        'ticket_id': ticket_id,
        'status': 'Hacked',  # Not in VALID_STATUS_VALUES
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid status value' in response.data
