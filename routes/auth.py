"""
routes/auth.py – Authentication Routes
========================================
Handles user registration, login, logout, account deletion, and
clearing the profile picture.

Routes:
  POST /auth/login             – Validate credentials and log the user in
  POST /auth/register          – Create a new account and log in immediately
  GET  /auth/logout            – Log the current user out
  POST /auth/delete_account    – Permanently delete the user's account (AJAX)
  POST /auth/clear_profile_pic – Reset profile picture to the default (AJAX)

All form submissions redirect to the home page on success or failure.
AJAX endpoints return JSON so JavaScript can handle the response.
"""

from flask import current_app
from flask import (
    Blueprint, request, redirect, url_for,
    flash, render_template, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User

# Create the blueprint (prefix = /auth)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ──────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Process the login form submitted from the login modal.
    Validates username/email + password, then logs the user in.
    """

    # Get form values (sent as regular POST, Chapter 17)
    identifier = request.form.get('identifier', '').strip()
    password   = request.form.get('password', '')

    # Basic server-side validation (client-side JS also checks these)
    if not identifier or not password:
        flash('Please fill in all fields.', 'danger')
        return redirect(url_for('main.home'))

    # Look up user by username OR email
    user = (
        User.query.filter_by(username=identifier).first()
        or User.query.filter_by(email=identifier).first()
    )

    # Check credentials
    if user is None or not user.check_password(password):
        flash('Invalid username/email or password.', 'danger')
        return redirect(url_for('main.home'))

    # Log the user in (Flask-Login sets the session cookie)
    login_user(user, remember=True)
    flash(f'Welcome back, {user.username}!', 'success')

    # Redirect to the page the user was trying to visit, or home
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Process the registration form from the register modal.
    Creates a new user in the database with a hashed password.
    """

    # Get form values
    username  = request.form.get('username',  '').strip()
    email     = request.form.get('email',     '').strip().lower()
    password  = request.form.get('password',  '')
    password2 = request.form.get('password2', '')

    # ── Server-side validation ────────────────────────────────

    if not username or not email or not password:
        flash('All fields are required.', 'danger')
        return redirect(url_for('main.home'))

    if password != password2:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('main.home'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('main.home'))

    # Check if username or email already taken
    if User.query.filter_by(username=username).first():
        flash('That username is already taken. Try another.', 'danger')
        return redirect(url_for('main.home'))

    if User.query.filter_by(email=email).first():
        flash('An account with that email already exists.', 'danger')
        return redirect(url_for('main.home'))

    # Prevent registering as super_admin username
    from flask import current_app
    if username.lower() == current_app.config['SUPER_ADMIN_USERNAME'].lower():
        flash('That username is reserved.', 'danger')
        return redirect(url_for('main.home'))

    # ── Create the new user ───────────────────────────────────

    new_user = User(username=username, email=email)
    new_user.set_password(password)  # Werkzeug hashes the password

    db.session.add(new_user)
    db.session.commit()

    # Log them in right away after registering
    login_user(new_user, remember=True)
    flash(f'Welcome to dotTopic, {new_user.username}!', 'success')

    return redirect(url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    """Log the current user out and redirect to home."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# DELETE ACCOUNT
# ──────────────────────────────────────────────────────────────

@auth_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete the current user's account and all related data."""
    user = current_user._get_current_object()  # get real user object
    logout_user()
    db.session.delete(user)   # cascade should remove related records
    db.session.commit()
    return jsonify({'status': 'success', 'redirect': url_for('main.home')})

# ──────────────────────────────────────────────────────────────
# CLEAR PROFILE PICTURE
# ──────────────────────────────────────────────────────────────

@auth_bp.route('/clear_profile_pic', methods=['POST'])
@login_required
def clear_profile_pic():
    """
    POST /auth/clear_profile_pic   (AJAX, login required)
    Reset the logged-in user's profile picture back to the default.
    If they had a custom uploaded image, that file is also deleted from disk
    so it does not waste storage. Sets profile_pic to 'default_pfp.png'.
    Returns JSON: { "status": "success" }
    """
    user = current_user._get_current_object()
    # Only delete the file if it's a custom uploaded one, not a default
    if user.profile_pic and user.profile_pic not in ('default_pfp.png', 'default.png', 'images/default_pfp.png'):
        import os
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_pic)
        if os.path.exists(file_path):
            os.remove(file_path)
    user.profile_pic = 'default_pfp.png'
    db.session.commit()
    return jsonify({'status': 'success'})
