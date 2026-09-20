# IISAT QR deployment checklist

- Use PostgreSQL for public production deployment.
- Set a strong `SECRET_KEY`.
- Set `DATABASE_URL` to the production PostgreSQL URL.
- Set `PUBLIC_BASE_URL=https://your-domain.com`.
- Set `COOKIE_SECURE=1` when HTTPS is active.
- Change the default administrator password immediately.
- Confirm `/health` returns JSON with `status: ok`.
- Test QR attendance from a phone using mobile data as well as Wi-Fi.
- Create the active Academic Term before adding new production courses.
- Back up the database before importing large rosters or upgrading an existing installation.
- Use managed database backups/snapshots from the hosting provider.
