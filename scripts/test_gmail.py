"""Test rapido de Gmail API"""
import json, requests
from pathlib import Path

token_path = Path("token.json")
data = json.loads(token_path.read_text())

# Primero refrescar el token si está expirado
resp_refresh = requests.post(data["token_uri"], data={
    "client_id": data["client_id"],
    "client_secret": data["client_secret"],
    "refresh_token": data["refresh_token"],
    "grant_type": "refresh_token",
}, timeout=15)
print("Refresh status:", resp_refresh.status_code)
new_token = resp_refresh.json().get("access_token", data["token"])

headers = {"Authorization": f"Bearer {new_token}"}

resp = requests.get(
    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
    headers=headers,
    params={"q": "subject:Cierre de Caja has:attachment", "maxResults": 5},
    timeout=15
)
print("Gmail status:", resp.status_code)
print(resp.json())
