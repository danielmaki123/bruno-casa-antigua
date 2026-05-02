import json, os, requests, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from database.postgres import execute_query

load_dotenv()

def get_access_token():
    token_path = Path('token.json')
    data = json.loads(token_path.read_text(encoding='utf-8'))
    resp = requests.post(data['token_uri'], data={
        'client_id': data['client_id'],
        'client_secret': data['client_secret'],
        'refresh_token': data['refresh_token'],
        'grant_type': 'refresh_token',
    })
    return resp.json()['access_token']

def update_values(spreadsheet_id, range_name, values):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}?valueInputOption=USER_ENTERED'
    headers = {'Authorization': f'Bearer {get_access_token()}'}
    resp = requests.put(url, headers=headers, json={'values': values})
    return resp.json()

def add_sheet(spreadsheet_id, title):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate'
    headers = {'Authorization': f'Bearer {get_access_token()}'}
    body = {'requests': [{'addSheet': {'properties': {'title': title}}}]}
    resp = requests.post(url, headers=headers, json=body)
    return resp.json()

sheet_id = '151xfpywCXxX_4gXFac-3aGQ_ttQ_pZY_6OOjA5llx_A'

# 1. Definir categorías de bebidas estrictas
cat_bebidas = ['GASEOSAS', 'BEBIDAS NATURALES', 'BEERS', 'CERVEZAS EXTRANJERAS', 'CERVEZAS FALK', 'LICORES', 'RONES', 'VINO', 'SANGRIA', 'COCTELES DE LA CASA']

# 2. Extraer platos de estas categorías desde SQL
placeholders = ','.join(['%s'] * len(cat_bebidas))
query = f"SELECT DISTINCT categoria, descripcion FROM ventas_detalle WHERE categoria IN ({placeholders}) ORDER BY categoria, descripcion"
rows = execute_query(query, cat_bebidas, fetch=True)

if not rows:
    print("No se encontraron bebidas en la base de datos.")
else:
    df_bebidas = pd.DataFrame(rows)
    df_bebidas.columns = ['CATEGORIA', 'PLATO_POS']
    df_bebidas['INGREDIENTE_INVENTARIO'] = ''
    df_bebidas['CANTIDAD'] = ''
    df_bebidas['UNIDAD'] = ''

    # 3. Crear pestaña BEBIDAS y subir datos
    add_sheet(sheet_id, 'BEBIDAS')
    values = [df_bebidas.columns.tolist()] + df_bebidas.values.tolist()
    update_values(sheet_id, 'BEBIDAS!A1', values)
    print('Pestaña BEBIDAS creada y poblada.')
