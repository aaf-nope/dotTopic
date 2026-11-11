"""
routes/users.py – User Profile & Account Routes
=================================================
Chapter 17: Flask Blueprints, session management.
Chapter 18: SQLAlchemy queries for user data.

Routes:
  GET  /u/<username>           – User profile page (their posts)
  POST /u/settings/email       – Change email (from account modal)
  POST /u/settings/username    – Change username
  POST /u/settings/password    – Change password
  POST /u/settings/avatar      – Upload new profile picture
"""

import os
import uuid

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort, current_app
)
from flask_login import login_required, current_user

from models import db, User, Post, LikeDislike

# Create the blueprint
users_bp = Blueprint('users', __name__)


# ──────────────────────────────────────────────────────────────
# HELPER: save a profile picture
# ──────────────────────────────────────────────────────────────

def _save_avatar(file_obj):
    """Save an uploaded profile picture. Returns the filename or None."""

    if not file_obj or file_obj.filename == '':
        return None

    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_AVATAR_EXTENSIONS']:
        return None
    filename  = f'{uuid.uuid4().hex}.{ext}'
    save_dir  = os.path.join(current_app.config['UPLOAD_FOLDER'], 'uploads', 'profile_pics')
    save_path = os.path.join(save_dir, filename)
    file_obj.save(save_path)

    return f'uploads/profile_pics/{filename}'


# ──────────────────────────────────────────────────────────────
# USER PROFILE PAGE  (route: /u/<username>)
# ──────────────────────────────────────────────────────────────

@users_bp.route('/u/<string:username>')
def user_profile(username):
    """
    Display a user's public profile page showing all their posts.
    If the viewer is the same user, show edit/delete buttons.
    """

    # Find the user (404 if not found)
    profile_user = User.query.filter_by(username=username).first_or_404()

    # Get their posts, newest first
    posts = (
        Post.query
        .filter_by(user_id=profile_user.id)
        .order_by(Post.created_at.desc())
        .all()
    )

    # True if the logged-in user is viewing their own page
    is_own_profile = (
        current_user.is_authenticated
        and current_user.id == profile_user.id
    )

    # Attach user_vote to each post for like/dislike button state
    if current_user.is_authenticated and posts:
        user_likes = {
            like.post_id: like.value
            for like in LikeDislike.query
            .filter_by(user_id=current_user.id)
            .filter(LikeDislike.post_id.in_([p.id for p in posts]))
            .all()
        }
    else:
        user_likes = {}
    for post in posts:
        post.user_vote = user_likes.get(post.id, 0)

    return render_template(
        'user.html',
        profile_user   = profile_user,
        posts          = posts,
        is_own_profile = is_own_profile
    )


# ──────────────────────────────────────────────────────────────
# CHANGE EMAIL  (route: POST /u/settings/email)
# ──────────────────────────────────────────────────────────────

@users_bp.route('/u/settings/email', methods=['POST'])
@login_required
def change_email():
    """Update the logged-in user's email address."""

    new_email = request.form.get('new_email', '').strip().lower()

    if not new_email:
        flash('Email cannot be empty.', 'danger')
        return redirect(url_for('main.home'))

    # Check if email is already in use by someone else
    if User.query.filter_by(email=new_email).first():
        flash('That email is already in use.', 'danger')
        return redirect(url_for('main.home'))

    current_user.email = new_email
    db.session.commit()

    flash('Email updated successfully!', 'success')
    return redirect(url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# CHANGE USERNAME  (route: POST /u/settings/username)
# ──────────────────────────────────────────────────────────────

@users_bp.route('/u/settings/username', methods=['POST'])
@login_required
def change_username():
    """Update the logged-in user's username."""

    new_username = request.form.get('new_username', '').strip()

    if not new_username:
        flash('Username cannot be empty.', 'danger')
        return redirect(url_for('main.home'))

    # Prevent taking the super admin username
    if new_username.lower() == current_app.config['SUPER_ADMIN_USERNAME'].lower():
        flash('That username is reserved.', 'danger')
        return redirect(url_for('main.home'))

    if User.query.filter_by(username=new_username).first():
        flash('That username is already taken.', 'danger')
        return redirect(url_for('main.home'))

    current_user.username = new_username
    db.session.commit()

    flash('Username updated successfully!', 'success')
    return redirect(url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# CHANGE PASSWORD  (route: POST /u/settings/password)
# ──────────────────────────────────────────────────────────────

@users_bp.route('/u/settings/password', methods=['POST'])
@login_required
def change_password():
    """Update the logged-in user's password after verifying the old one."""

    old_password  = request.form.get('old_password',  '')
    new_password  = request.form.get('new_password',  '')
    new_password2 = request.form.get('new_password2', '')

    # Verify the current password
    if not current_user.check_password(old_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('main.home'))

    if new_password != new_password2:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('main.home'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'danger')
        return redirect(url_for('main.home'))

    current_user.set_password(new_password)
    db.session.commit()

    flash('Password changed successfully!', 'success')
    return redirect(url_for('main.home'))


# ──────────────────────────────────────────────────────────────
# CHANGE AVATAR  (route: POST /u/settings/avatar)
# ──────────────────────────────────────────────────────────────

@users_bp.route('/u/settings/avatar', methods=['POST'])
@login_required
def change_avatar():
    """Upload and set a new profile picture for the logged-in user."""

    file_obj = request.files.get('avatar')
    new_path = _save_avatar(file_obj)

    if not new_path:
        flash('Please upload a valid image (png, jpg, jpeg, gif).', 'danger')
        return redirect(url_for('users.user_profile', username=current_user.username))

    current_user.profile_pic = new_path
    db.session.commit()

    flash('Profile picture updated!', 'success')
    return redirect(url_for('users.user_profile', username=current_user.username))
