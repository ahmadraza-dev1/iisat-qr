# IISAT QR architecture

IISAT QR uses Flask's application-factory pattern and keeps HTTP routing,
business logic, persistence, reports, and static UI assets separated.

## Main layers

- `presenceqr/__init__.py` — application factory only.
- `presenceqr/config.py` — environment-based runtime configuration.
- `presenceqr/extensions.py` — shared Flask extensions.
- `presenceqr/models.py` — SQLAlchemy domain models and relationships.
- `presenceqr/routes/` — endpoint modules grouped by feature area.
- `presenceqr/services/` — reusable business logic and database bootstrap.
- `presenceqr/reports.py` — Excel/PDF report generation.
- `presenceqr/security.py` — rotating signed QR token logic.
- `presenceqr/templates/` — server-rendered Jinja UI.
- `presenceqr/static/` — CSS, JavaScript, and PWA metadata.
- `tests/` — regression tests for critical attendance flows.

## Adding a feature

1. Add or extend a model only when persistence is required.
2. Put reusable calculations/workflows under `services/`.
3. Add HTTP endpoints to the closest module under `routes/`.
4. Add the matching template/static assets.
5. Add a regression test before deployment.

The internal Python package remains named `presenceqr` intentionally so an
existing deployment/database can be upgraded without unnecessary import or
migration risk. The product-facing name is **IISAT QR**.
