"""
config.py – dotTopic Application Configuration
================================================
All app-wide settings live here. Import Config in app.py.
Chapter 17: Flask configuration patterns.
"""

import os


class Config:
    # ──────────────────────────────────────────────
    # Core Flask settings
    # ──────────────────────────────────────────────

    # Secret key used to sign session cookies. Keep this private!
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dottopic-super-secret-key-2026'

    # ──────────────────────────────────────────────
    # Database – SQLite via SQLAlchemy (Chapter 18)
    # ──────────────────────────────────────────────

    # SQLite file is created in the project root automatically
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dottopic.db'

    # Disable modification tracking (not needed, saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ──────────────────────────────────────────────
    # File Uploads (Chapter 17 – request.files)
    # ──────────────────────────────────────────────

    # Where uploaded files are saved on the server
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static')

    # Maximum upload size: 16 MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Allowed file extensions for post media
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov'}

    # Allowed extensions for profile pictures
    ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # ──────────────────────────────────────────────
    # Super Admin (hardcoded – NOT via registration)
    # ──────────────────────────────────────────────

    SUPER_ADMIN_USERNAME = os.environ.get('SUPER_ADMIN_USERNAME') or 'admin'
    SUPER_ADMIN_EMAIL    = os.environ.get('SUPER_ADMIN_EMAIL') or 'admin@dottopic.com'
    SUPER_ADMIN_PASSWORD = os.environ.get('SUPER_ADMIN_PASSWORD') or 'admin123'
