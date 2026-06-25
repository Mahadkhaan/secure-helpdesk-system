"""Security-header tests: verify the after_request hook injects every header."""


def test_x_content_type_options(client):
    response = client.get('/')
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'


def test_x_frame_options(client):
    response = client.get('/')
    assert response.headers.get('X-Frame-Options') == 'DENY'


def test_referrer_policy(client):
    response = client.get('/')
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


def test_permissions_policy(client):
    response = client.get('/')
    pp = response.headers.get('Permissions-Policy', '')
    assert 'camera=()' in pp
    assert 'microphone=()' in pp
    assert 'geolocation=()' in pp


def test_csp_present(client):
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy', '')
    assert "default-src 'self'" in csp


def test_csp_restricts_scripts(client):
    """Scripts are limited to self and the Bootstrap CDN — no inline scripts allowed."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy', '')
    assert 'script-src' in csp
    assert 'https://cdn.jsdelivr.net' in csp
    # 'unsafe-inline' must NOT appear in the script-src directive
    # Parse only the script-src token to avoid matching style-src
    directives = {d.strip(): d.strip() for d in csp.split(';')}
    script_src = next((v for v in directives if v.startswith('script-src')), '')
    assert "'unsafe-inline'" not in script_src


def test_headers_present_on_error_pages(client):
    """Security headers are applied to error responses too."""
    response = client.get('/this-page-does-not-exist')
    assert response.status_code == 404
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'DENY'
