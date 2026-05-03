#!/usr/bin/env python3
import sys, os, base64, tempfile
sys.path.insert(0, '/app')
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from skills.parsers import parse_cierre_pdf

creds = Credentials.from_authorized_user_file('/app/token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
svc = build('gmail', 'v1', credentials=creds)

r = svc.users().messages().list(userId='me', q='has:attachment filename:CierrePos.pdf subject:cierre', maxResults=1).execute()
mid = r['messages'][0]['id']
msg = svc.users().messages().get(userId='me', id=mid, format='full').execute()

for p in msg['payload']['parts']:
    if p.get('filename') == 'CierrePos.pdf':
        att = svc.users().messages().attachments().get(userId='me', messageId=mid, id=p['body']['attachmentId']).execute()
        data = att['data'].replace('-', '+').replace('_', '/')
        pad = len(data) % 4
        if pad:
            data += '=' * (4 - pad)
        pdf_bytes = base64.b64decode(data)
        with open('/tmp/test_cierre.pdf', 'wb') as f:
            f.write(pdf_bytes)
        result = parse_cierre_pdf('/tmp/test_cierre.pdf')
        print("RESULT:", result)
        break
