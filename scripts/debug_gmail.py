"""Debug: trace exacto del error en gmail_monitor"""
import sys, traceback
sys.path.insert(0, '.')
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.') / '.env')

import requests, json

# Simular exactamente lo que hace gmail_monitor
s = requests.Session()
s.trust_env = False

data = json.loads(Path('token.json').read_text())
token = data['token']
headers = {'Authorization': f'Bearer {token}'}

try:
    resp = s.get(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages',
        headers=headers,
        params={'q': 'subject:"Cierre de Caja" has:attachment', 'maxResults': 5},
        timeout=15
    )
    print('OK status:', resp.status_code)
    print(resp.json())
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
