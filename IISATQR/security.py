"""Security helpers for rotating, signed attendance QR tokens."""

import hashlib
import hmac
import time

from flask import current_app


def current_slot():
    """Return the active QR time slot based on configured rotation seconds."""
    return int(time.time()) // current_app.config["QR_ROTATION_SECONDS"]


def make_qr_token(session_id):
    """Create a short HMAC-signed token for an attendance session."""
    slot = current_slot()
    body = f"{session_id}.{slot}"
    signature = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()[:28]
    return f"{body}.{signature}"


def verify_qr_token(token):
    """Validate a token from the current or immediately previous QR slot."""
    try:
        session_id_text, slot_text, signature = token.split(".", 2)
        session_id = int(session_id_text)
        slot = int(slot_text)
    except (ValueError, AttributeError):
        return None

    # Accepting the immediately previous slot prevents a legitimate submission
    # from failing when the QR rotates between the scan and the form submit.
    if slot not in {current_slot(), current_slot() - 1}:
        return None

    body = f"{session_id}.{slot}"
    expected = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()[:28]

    if not hmac.compare_digest(signature, expected):
        return None

    return {"sid": session_id, "slot": slot}
