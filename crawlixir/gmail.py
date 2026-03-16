"""Gmail integration - saves email drafts to your account."""

import base64
import json
import os
import pickle
from email.mime.text import MIMEText
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
TOKEN_PATH = Path.home() / ".crawlixir" / "gmail_token.pickle"
CREDENTIALS_PATH = Path.home() / ".crawlixir" / "credentials.json"


def _get_service():
    """Authenticate and return a Gmail API service instance."""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Gmail integration requires extra dependencies. Install them with:\n"
            "  pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    creds = None
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {CREDENTIALS_PATH}\n\n"
                    "Setup instructions:\n"
                    "  1. Go to https://console.cloud.google.com\n"
                    "  2. Create a new project\n"
                    "  3. Enable the Gmail API\n"
                    "  4. Create OAuth 2.0 credentials (Desktop app)\n"
                    f"  5. Download and save as {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def create_draft(subject, body, to=None):
    """
    Save an email as a draft in Gmail.
    Returns a dict with the draft id and a link to open it.
    """
    service = _get_service()

    message = MIMEText(body)
    message["subject"] = subject
    if to:
        message["to"] = to

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}},
    ).execute()

    draft_id = draft["id"]
    message_id = draft["message"]["id"]

    return {
        "id": draft_id,
        "message_id": message_id,
        "url": f"https://mail.google.com/mail/#drafts/{message_id}",
    }
