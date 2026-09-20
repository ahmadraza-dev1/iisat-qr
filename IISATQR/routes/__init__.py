"""HTTP routes grouped by domain while preserving the original endpoints."""

from flask import Blueprint


bp = Blueprint("main", __name__)

# Public helpers are re-exported because the application factory injects them
# into templates and older code may import them from ``presenceqr.routes``.
from .helpers import current_teacher, get_setting  # noqa: E402,F401

# Import route modules after the blueprint exists so decorators can register.
from . import (  # noqa: E402,F401
    admin,
    analytics,
    attendance,
    auth,
    courses,
    dashboard,
    students,
    teachers,
    terms,
)
