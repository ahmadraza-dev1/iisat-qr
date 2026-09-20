# Local development (VS Code)

## Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Before changing code

Copy any real SQLite database in `instance/` to a safe backup location.
Production deployments should use environment variables from `.env.example`
and PostgreSQL rather than relying on a local SQLite file.
