import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_access_token():
    token_path = Path('token.json')
    data = json.loads(token_path.read_text(encoding='utf-8'))
    resp = requests.post(
        data['token_uri'],
        data={
            'client_id': data['client_id'],
            'client_secret': data['client_secret'],
            'refresh_token': data['refresh_token'],
            'grant_type': 'refresh_token',
        }
    )
    return resp.json()['access_token']

def list_sheets(spreadsheet_id):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
    headers = {'Authorization': f'Bearer {get_access_token()}'}
    resp = requests.get(url, headers=headers)
    metadata = resp.json()
    return [s['properties']['title'] for s in metadata.get('sheets', [])]

old_id = "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw"
new_id = "1F8g3UAlrT4ycXa3BjlINEOlllUX7YCUED4ch-Ufk6Hs"

print(f"VIEJO ({old_id}):")
print(list_sheets(old_id))
print(f"\nNUEVO ({new_id}):")
print(list_sheets(new_id))
