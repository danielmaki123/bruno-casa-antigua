#!/usr/bin/env python3
"""
Extrae y muestra el texto de los PDFs del último cierre.
Run: python scripts/debug_pdf.py
"""
import os
import sys
import tempfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pypdf import PdfReader

GMAIL_QUERY = "has:attachment filename:pdf subject:cierre from:notificaciones@solusystemsni.com"
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "/app/token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("gmail", "v1", credentials=creds)


def download_attachment(service, message_id, attachment_id):
    att = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    import base64
    data = att["data"].replace("-", "+").replace("_", "/")
    pad = len(data) % 4
    if pad:
        data += "=" * (4 - pad)
    return base64.b64decode(data)


def main():
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me", q=GMAIL_QUERY, maxResults=1
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No emails found.")
        sys.exit(1)

    msg_id = messages[0]["id"]
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    parts = msg.get("payload", {}).get("parts", [])

    for part in parts:
        filename = part.get("filename", "")
        mime = part.get("mimeType", "")
        att_id = part.get("body", {}).get("attachmentId")

        if att_id and (mime == "application/pdf" or filename.lower().endswith(".pdf")):
            print(f"\n{'='*60}")
            print(f"FILE: {filename}")
            print(f"{'='*60}")

            pdf_bytes = download_attachment(service, msg_id, att_id)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_bytes)
                tmp = f.name

            try:
                reader = PdfReader(tmp)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    print(f"--- Page {i+1} (human) ---\n{text}")
                    print(f"--- Page {i+1} (repr, first 800 chars) ---")
                    print(repr(text[:800]))
            finally:
                os.unlink(tmp)


if __name__ == "__main__":
    main()
