import json, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / 'token.json').read_text(encoding='utf-8'))
s = requests.Session()
s.trust_env = False
token = data['token']
headers = {'Authorization': 'Bearer ' + token}

r = s.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers, timeout=10)
info = r.json()
print('Cuenta Google:', info.get('email', 'N/A'))

r2 = s.get('https://www.googleapis.com/drive/v3/files',
    headers=headers,
    params={
        'q': 'mimeType="application/vnd.google-apps.spreadsheet" and trashed=false',
        'fields': 'files(id,name,webViewLink)',
        'orderBy': 'createdTime desc',
        'pageSize': 15
    },
    timeout=10)
files = r2.json().get('files', [])
print(f'\nSheets encontrados ({len(files)}):')
for f in files:
    print(f"  {f['name']}")
    print(f"  {f['webViewLink']}")
    print()
