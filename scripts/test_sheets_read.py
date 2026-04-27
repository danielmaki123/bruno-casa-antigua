import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')

def test_read():
    if not os.path.exists('token.json'):
        print("❌ Error: No se encontró token.json")
        return

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    # Obtener metadatos de la hoja
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get('sheets', [])
    
    print(f"Conexion exitosa con el Sheet: {spreadsheet.get('properties').get('title')}")
    print("Pestañas encontradas:")
    for sheet in sheets:
        print(f"- {sheet.get('properties').get('title')}")

if __name__ == '__main__':
    test_read()
