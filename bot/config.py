import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"[ERROR] {key} no configurado en .env")
        sys.exit(1)
    return val


TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
KIMI_API_KEY = _require("KIMI_API_KEY")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
DATABASE_URL = _require("DATABASE_URL")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

GROUP_ID_INVENTARIO = int(_require("GROUP_ID_INVENTARIO"))
GROUP_ID_ADMIN = int(_require("GROUP_ID_ADMIN"))
GROUP_ID_TEAM = int(_require("GROUP_ID_TEAM"))

AUTHORIZED_USERS = set(
    int(uid.strip())
    for uid in _require("AUTHORIZED_USERS").split(",")
    if uid.strip()
)

WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
