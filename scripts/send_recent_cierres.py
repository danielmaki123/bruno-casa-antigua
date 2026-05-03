#!/usr/bin/env python3
"""
Fetch last N cierre PDFs from Gmail and POST to BrunoBot webhook.
Run from EasyPanel terminal: python scripts/send_recent_cierres.py
"""
import os
import sys
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

WEBHOOK_URL = "http://localhost:8080/webhook/cierre/pdf"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
N_CIERRES = int(os.getenv("N_CIERRES", "2"))
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
    # Gmail returns base64url — convert to standard base64
    data = att["data"].replace("-", "+").replace("_", "/")
    pad = len(data) % 4
    if pad:
        data += "=" * (4 - pad)
    return data


def get_pdf_attachments(service, message_id):
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    attachments = []
    parts = msg.get("payload", {}).get("parts", [])

    for part in parts:
        filename = part.get("filename", "")
        mime = part.get("mimeType", "")
        att_id = part.get("body", {}).get("attachmentId")

        if att_id and (mime == "application/pdf" or filename.lower().endswith(".pdf")):
            print(f"    Descargando: {filename}")
            data = download_attachment(service, message_id, att_id)
            attachments.append({"filename": filename or "cierre.pdf", "data": data})

    return attachments


def send_to_brunobot(attachments):
    resp = requests.post(
        WEBHOOK_URL,
        json={"attachments": attachments},
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Secret": WEBHOOK_SECRET,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"[1/3] Conectando a Gmail...")
    try:
        service = get_gmail_service()
    except FileNotFoundError:
        print(f"ERROR: No se encontró {TOKEN_FILE}")
        print("Verificá que token.json esté montado en EasyPanel → File Mounts.")
        sys.exit(1)

    print(f"[2/3] Buscando últimos {N_CIERRES} cierres...")
    results = service.users().messages().list(
        userId="me", q=GMAIL_QUERY, maxResults=N_CIERRES
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No se encontraron emails de cierre.")
        sys.exit(1)

    print(f"  Encontrados: {len(messages)} emails")

    print(f"[3/3] Procesando y enviando a BrunoBot...")
    for i, ref in enumerate(messages, 1):
        msg_id = ref["id"]
        print(f"\n  Cierre {i}/{len(messages)} (ID: {msg_id})")

        pdfs = get_pdf_attachments(service, msg_id)
        if not pdfs:
            print("    Sin PDFs, saltando.")
            continue

        print(f"    Enviando {len(pdfs)} PDF(s)...")
        try:
            result = send_to_brunobot(pdfs)
            print(f"    OK: {result}")
        except Exception as e:
            print(f"    ERROR: {e}")

    print("\nListo.")


if __name__ == "__main__":
    main()
