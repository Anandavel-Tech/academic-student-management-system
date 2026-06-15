from functools import wraps
from flask import g, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in', False):  # Check for boolean value
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username, password):
    users = g.db.users
    user = users.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        return True
    return False

def create_user(username, password):
    users = g.db.users
    if users.find_one({'username': username}):
        return False
    users.insert_one({
        'username': username,
        'password': generate_password_hash(password)
    })
    return True
