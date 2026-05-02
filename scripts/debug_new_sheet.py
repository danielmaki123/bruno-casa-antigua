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

def get_values(spreadsheet_id, range_name):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}'
    headers = {'Authorization': f'Bearer {get_access_token()}'}
    resp = requests.get(url, headers=headers)
    return resp.json().get('values', [])

new_id = "1F8g3UAlrT4ycXa3BjlINEOlllUX7YCUED4ch-Ufk6Hs"
print("FILAS STOCK_DIARIO (Primeras 5):")
for row in get_values(new_id, "STOCK_DIARIO!A1:Z5"):
    print(row)

print("\nFILAS PRODUCTOS (Primeras 5):")
for row in get_values(new_id, "PRODUCTOS!A1:Z5"):
    print(row)
