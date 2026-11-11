"""
routes/__init__.py
==================
This empty file marks the 'routes' folder as a Python package.
Without it, Python would not allow 'from routes.auth import auth_bp'.

The actual routes (URL handlers) are split across:
  - auth.py   : login, register, logout, account management
  - main.py   : home page, search
  - topics.py : topic pages, posts, moderation actions
  - users.py  : user profile pages, settings
  - api.py    : REST API endpoints (return JSON for AJAX calls)

All blueprints are imported individually in app.py and registered with
the Flask app there.
"""
