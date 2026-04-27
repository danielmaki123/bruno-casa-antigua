import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')

def initialize_sheets():
    if not os.path.exists('token.json'):
        print("❌ Error: No se encontró token.json")
        return

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    # Definir la estructura
    tabs = {
        'INVENTARIO': ['fecha', 'turno', 'area', 'insumo_id', 'cantidad_fisica', 'responsable', 'notas'],
        'INSUMOS': ['insumo_id', 'nombre', 'unidad_base', 'stock_minimo', 'stock_critico', 'proveedor_default', 'contacto', 'area_default'],
        'RECETAS': ['receta_id', 'nombre', 'insumo', 'cantidad', 'unidad', 'categoria'],
        'VENTAS_DIARIAS': ['fecha', 'receta_id', 'cantidad_vendida', 'ingreso_total', 'cajero', 'notas'],
        'EMPLEADOS': ['empleado_id', 'nombre', 'funcion', 'fecha_ingreso', 'telefono', 'estado', 'area'],
        'EVENTOS_CALENDARIO': ['fecha', 'tipo', 'descripcion', 'monto_estimado', 'estado', 'notas']
    }

    # Obtener hojas actuales para no duplicar
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing_sheets = {s.get('properties').get('title'): s.get('properties').get('sheetId') for s in spreadsheet.get('sheets', [])}

    requests = []

    # 1. Renombrar 'Hoja 1' a 'INVENTARIO' si existe y no existe ya INVENTARIO
    if 'Hoja 1' in existing_sheets and 'INVENTARIO' not in existing_sheets:
        requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': existing_sheets['Hoja 1'],
                    'title': 'INVENTARIO'
                },
                'fields': 'title'
            }
        })
        existing_sheets['INVENTARIO'] = existing_sheets.pop('Hoja 1')

    # 2. Crear las pestañas faltantes
    for sheet_name in tabs.keys():
        if sheet_name not in existing_sheets:
            requests.append({
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            })

    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()
        # Refrescar IDs después de crear
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = {s.get('properties').get('title'): s.get('properties').get('sheetId') for s in spreadsheet.get('sheets', [])}

    # 3. Escribir encabezados
    value_input_option = 'RAW'
    for sheet_name, headers in tabs.items():
        range_name = f"'{sheet_name}'!A1"
        body = {'values': [headers]}
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption=value_input_option, body=body).execute()

    print("Google Sheets inicializado con todas las pestanas y encabezados.")

if __name__ == '__main__':
    initialize_sheets()
