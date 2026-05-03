#!/usr/bin/env python3
"""
import_historico.py — Importa TODOS los cierres históricos de Gmail a Bruno DB.

Uso desde terminal EasyPanel:
    python scripts/import_historico.py

Opciones (env vars):
    DESDE_FECHA=2024-01-01   Solo emails desde esta fecha (formato YYYY-MM-DD)
    HASTA_FECHA=2026-12-31   Solo emails hasta esta fecha
    DRY_RUN=1                Solo muestra qué procesaría, no envía nada
    WEBHOOK_URL=...          Default: http://localhost:8080/webhook/cierre/pdf
"""
import os
import sys
import time
import base64
from datetime import datetime

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

WEBHOOK_URL   = os.getenv("WEBHOOK_URL", "http://localhost:8080/webhook/cierre/pdf")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
TOKEN_FILE    = os.getenv("GOOGLE_TOKEN_FILE", "/app/token.json")
SCOPES        = ["https://www.googleapis.com/auth/gmail.readonly"]
DRY_RUN       = os.getenv("DRY_RUN", "0") == "1"
DESDE_FECHA   = os.getenv("DESDE_FECHA", "")
HASTA_FECHA   = os.getenv("HASTA_FECHA", "")
DELAY_SEG     = float(os.getenv("DELAY_SEG", "0.5"))  # pausa entre emails

BASE_QUERY = "has:attachment filename:pdf subject:cierre from:notificaciones@solusystemsni.com"


def build_query() -> str:
    q = BASE_QUERY
    if DESDE_FECHA:
        dt = datetime.strptime(DESDE_FECHA, "%Y-%m-%d")
        q += f" after:{dt.strftime('%Y/%m/%d')}"
    if HASTA_FECHA:
        dt = datetime.strptime(HASTA_FECHA, "%Y-%m-%d")
        q += f" before:{dt.strftime('%Y/%m/%d')}"
    return q


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("gmail", "v1", credentials=creds)


def get_all_message_ids(service, query: str) -> list:
    ids = []
    page_token = None
    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.users().messages().list(**kwargs).execute()
        ids.extend(result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
        print(f"  Paginando... {len(ids)} emails encontrados hasta ahora")
    return ids


def download_attachment(service, message_id, attachment_id) -> str:
    att = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    data = att["data"].replace("-", "+").replace("_", "/")
    pad = len(data) % 4
    if pad:
        data += "=" * (4 - pad)
    return data


def get_pdf_attachments(service, message_id) -> list:
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
            data = download_attachment(service, message_id, att_id)
            attachments.append({"filename": filename or "cierre.pdf", "data": data})
    return attachments


def send_to_brunobot(attachments) -> dict:
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


def get_email_date(service, message_id) -> str:
    msg = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["Date"]
    ).execute()
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Date":
            return h["value"][:16]
    return "fecha desconocida"


def main():
    query = build_query()
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Iniciando importación histórica")
    print(f"Query: {query}")
    if DESDE_FECHA:
        print(f"Desde: {DESDE_FECHA}")
    if HASTA_FECHA:
        print(f"Hasta: {HASTA_FECHA}")
    print()

    try:
        service = get_gmail_service()
    except FileNotFoundError:
        print(f"ERROR: No se encontró {TOKEN_FILE}")
        sys.exit(1)

    print("Buscando todos los emails...")
    messages = get_all_message_ids(service, query)
    total = len(messages)

    if not total:
        print("No se encontraron emails con los filtros aplicados.")
        sys.exit(0)

    print(f"Total emails encontrados: {total}\n")

    ok = dupes = errors = sin_pdf = 0

    for i, ref in enumerate(messages, 1):
        msg_id = ref["id"]
        fecha = get_email_date(service, msg_id)
        print(f"[{i}/{total}] {fecha} (ID: {msg_id})", end=" ")

        if DRY_RUN:
            print("→ DRY RUN, saltando")
            continue

        pdfs = get_pdf_attachments(service, msg_id)
        if not pdfs:
            print("→ sin PDFs")
            sin_pdf += 1
            continue

        try:
            result = send_to_brunobot(pdfs)
            if result.get("duplicado"):
                print(f"→ duplicado (ya existe)")
                dupes += 1
            else:
                doc = result.get("documento_id", "?")
                print(f"→ OK doc {doc}")
                ok += 1
        except Exception as e:
            print(f"→ ERROR: {e}")
            errors += 1

        time.sleep(DELAY_SEG)

    print(f"""
=== RESUMEN ===
Total emails:   {total}
Importados:     {ok}
Duplicados:     {dupes} (ya estaban en DB)
Sin PDF:        {sin_pdf}
Errores:        {errors}
""")


if __name__ == "__main__":
    main()
