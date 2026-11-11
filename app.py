"""
app.py – dotTopic Application Entry Point
==========================================
This is the first file Flask looks at when the server starts.
It uses the "app factory" pattern: a function (create_app) builds and
configures the Flask application so it can be tested or extended easily.

How to run:
    python app.py   →  starts the development server at http://127.0.0.1:5000

What this file does:
  1. Creates a Flask app and loads settings from config.py
  2. Initialises the database (SQLAlchemy) and login system (Flask-Login)
  3. Registers all route Blueprints (auth, main, topics, users, api)
  4. Creates the database tables if they don't exist
  5. Ensures the super-admin account exists in the database
"""

import os
from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User


# ──────────────────────────────────────────────────────────────
# Flask-Login setup
# ──────────────────────────────────────────────────────────────
# LoginManager handles who is logged in, persisting the user across
# requests via a session cookie.

login_manager = LoginManager()

# If an unauthenticated user tries to reach a @login_required route,
# redirect them to the home page (which shows the login modal).
login_manager.login_view = 'main.home'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """
    Required by Flask-Login.
    Called on every request to reload the logged-in user from the database
    using the user ID stored in the session cookie.
    Returns a User object or None.
    """
    return User.query.get(int(user_id))


# ──────────────────────────────────────────────────────────────
# App Factory
# ──────────────────────────────────────────────────────────────

def create_app(config_class=Config):
    """
    Build and return the configured Flask application.

    Using the factory pattern (a function that creates the app) rather than
    creating the app at the module level makes it easier to test and to run
    multiple configurations (e.g. testing vs. production).

    Steps:
      1. Create the Flask instance
      2. Load config (secret key, database URI, upload folder, etc.)
      3. Ensure upload directories exist on disk
      4. Attach extensions (db, login_manager)
      5. Register route blueprints
      6. Create DB tables (if not already present)
      7. Seed the super-admin account
    """

    app = Flask(__name__)

    # Load all settings from the Config class in config.py
    app.config.from_object(config_class)

    # Make sure the directories where uploaded files will be saved actually exist.
    # exist_ok=True means no error if they already exist.
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'post_media'),   exist_ok=True)

    # ── Attach extensions to this app instance ────────────────
    # Extensions need to be linked to a specific app so they know
    # which database, config, etc. to use.
    db.init_app(app)
    login_manager.init_app(app)

    # ── Register Blueprints ───────────────────────────────────
    # Each blueprint is a group of related routes defined in its own file.
    # Importing here (not at the top) avoids circular import issues.
    from routes.auth   import auth_bp    # /auth/login, /auth/register, etc.
    from routes.main   import main_bp    # /, /search
    from routes.topics import topics_bp  # /t/<name>, /t/new, post routes
    from routes.users  import users_bp   # /u/<username>, account settings
    from routes.api    import api_bp     # /api/... (JSON responses for AJAX)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(topics_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(api_bp)

    # ── Initialise database ───────────────────────────────────
    # Run inside app_context so SQLAlchemy knows which app's DB to use.
    with app.app_context():
        # Creates all tables defined in models.py (skips existing ones).
        db.create_all()
        # Make sure the site's super-admin account exists.
        _seed_super_admin(app)

    return app


def _seed_super_admin(app):
    """
    Ensure the super-admin user account exists in the database.

    This is called once every time the app starts. If the account already
    exists, it just verifies that is_super_admin is True.
    Credentials come from config.py (SUPER_ADMIN_USERNAME / EMAIL / PASSWORD).

    Why not use seed.py for this?
    Because seed.py drops and recreates everything. The super-admin should
    survive database reseeds that happen during development.
    """
    existing = User.query.filter_by(username=app.config['SUPER_ADMIN_USERNAME']).first()

    if existing is None:
        # First run: create the super-admin account
        admin = User(
            username      = app.config['SUPER_ADMIN_USERNAME'],
            email         = app.config['SUPER_ADMIN_EMAIL'],
            is_super_admin= True
        )
        admin.set_password(app.config['SUPER_ADMIN_PASSWORD'])
        db.session.add(admin)
        db.session.commit()
        print(f"[dotTopic] Super admin '{admin.username}' created.")
    else:
        # Account exists – make sure it still has admin status (safety check)
        if not existing.is_super_admin:
            existing.is_super_admin = True
            db.session.commit()


# ──────────────────────────────────────────────────────────────
# Application startup
# ──────────────────────────────────────────────────────────────

# Create the global app instance (used by Gunicorn or the dev server)
app = create_app()

if __name__ == '__main__':
    # Only runs when called directly with `python app.py`
    # debug=True: auto-reloads on code changes, shows detailed error pages
    app.run(debug=True, port=5001)
