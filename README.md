# IISAT QR — Department Attendance Management Platform

IISAT QR is a responsive Flask-based attendance platform built for IISAT
University department/HOD workflows. It supports administrator/HOD control,
teacher accounts, academic terms, course assignment, rosters, rotating QR
attendance, correction/audit history, analytics, low-attendance visibility,
and Excel/PDF reporting.

## Core capabilities

- HOD/admin and teacher role separation
- Academic terms such as Fall 2024 / Spring 2025
- Searchable, term-filtered course management
- Multi-teacher course assignment
- Student rosters and CSV import
- Secure rotating QR attendance sessions
- Automatic Present/Absent records
- Teacher/admin attendance correction with mandatory audit reason
- Course and student attendance analytics
- Low-attendance threshold alerts
- Session history and individual student detail
- Excel and PDF reports
- Course archive/restore and audit log
- Responsive desktop/mobile UI
- SQLite for local development; PostgreSQL-ready for deployment
- Health endpoint and reverse-proxy support

## Repository layout

```text
IISAT_QR_Professional/
├── presenceqr/
│   ├── routes/          # HTTP endpoints grouped by feature
│   ├── services/        # Reusable business logic
│   ├── static/          # CSS / JavaScript / manifest
│   ├── templates/       # Jinja pages
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── reports.py
│   └── security.py
├── tests/
├── docs/
├── run.py               # local development
├── wsgi.py              # production server entrypoint
├── requirements.txt
├── render.yaml
├── Dockerfile
└── .env.example
```

## Run in VS Code

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## First-run administrator

Development defaults are preserved for compatibility:

- Staff ID: `ADMIN-001`
- Email: `admin@iisat.edu.pk`
- Password: `PresenceQR@123`

Change the password immediately after first login and set production values
through environment variables before putting the system on the public web.

## Production

Use `wsgi.py` with Gunicorn. A Render configuration and Dockerfile are
included. For persistent production data, use PostgreSQL and configure
`DATABASE_URL`, `SECRET_KEY`, `PUBLIC_BASE_URL`, and `COOKIE_SECURE=1`.

See `docs/DEPLOYMENT_CHECKLIST.md`, `docs/ARCHITECTURE.md`, and
`docs/LOCAL_DEVELOPMENT.md`.
