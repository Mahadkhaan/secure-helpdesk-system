from functools import wraps
from flask import abort, current_app, request
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'Admin':
            current_app.logger.warning(
                '[SECURITY] Non-admin accessed %s: user=%s ip=%s',
                request.url, current_user.username, request.remote_addr
            )
            abort(403)
        return f(*args, **kwargs)
    return decorated


def user_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'User':
            current_app.logger.warning(
                '[SECURITY] Non-user accessed %s: user=%s ip=%s',
                request.url, current_user.username, request.remote_addr
            )
            abort(403)
        return f(*args, **kwargs)
    return decorated
