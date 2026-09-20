# Render deployment guide

The repository includes `render.yaml`, so IISAT QR can be deployed as a Render Blueprint.

## 1. Push the project to GitHub

Create a private GitHub repository and push the **contents of this project folder** to the repository root.
Do not commit `.env`, local virtual environments, or SQLite database files.

## 2. Create a Render Blueprint

1. Sign in to Render.
2. Choose **New > Blueprint**.
3. Connect the GitHub repository.
4. Render reads `render.yaml` and creates the web service plus PostgreSQL database.
5. When prompted for `DEFAULT_ADMIN_PASSWORD`, enter a strong temporary administrator password.
6. Wait for the first deployment to finish.

## 3. Open the site

Render provides an HTTPS address similar to:

`https://iisat-qr.onrender.com`

The exact name depends on availability.

## 4. First login

Use the admin ID/email from your environment variables and the password you entered during Blueprint setup.
Immediately change the password from the profile page.

## 5. Custom domain (optional)

If you later buy a domain, add it from the Render service's **Settings > Custom Domains** page and follow the DNS instructions shown by Render.

## 6. Important production notes

- Do not use a local SQLite file on hosts with an ephemeral filesystem.
- Keep `COOKIE_SECURE=1` on HTTPS production deployments.
- Never commit production passwords or `SECRET_KEY` values.
- Back up production attendance data regularly.
- Free hosting/database plans are best for demos and evaluation. Review the provider's current persistence, sleep, and expiry limits before using them for live university records.
