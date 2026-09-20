"""Application configuration.

Runtime behavior intentionally matches the previous build. Production
values should be supplied through environment variables on the hosting
provider rather than committed to source control.
"""

import os


def database_url() -> str:
    """Return a SQLAlchemy-compatible database URL."""
    value = os.getenv("DATABASE_URL", "sqlite:///presenceqr.db")
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql://", 1)
    return value


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me-before-deployment")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QR_ROTATION_SECONDS = int(os.getenv("QR_ROTATION_SECONDS", "25"))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
