"""Flask extension instances shared by the application.

Keeping extension objects in one module avoids circular imports and makes
future integrations (migrations, caching, rate limiting, etc.) easier.
"""

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
