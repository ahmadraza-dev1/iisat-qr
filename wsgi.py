"""Production WSGI entrypoint."""

from presenceqr import create_app

app = create_app()
