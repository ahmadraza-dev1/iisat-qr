"""IISAT QR application factory."""

import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db
from .services.bootstrap import initialize_database


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Respect reverse-proxy headers when hosted behind Render/Nginx/etc.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    from .routes import bp, current_teacher, get_setting

    app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        return {
            "teacher": current_teacher(),
            "university_name": get_setting(
                "university_name",
                "IISAT University, Gujranwala",
            ),
            "attendance_threshold": float(
                get_setting("attendance_threshold", "75")
            ),
        }

    with app.app_context():
        initialize_database(app)

    return app
