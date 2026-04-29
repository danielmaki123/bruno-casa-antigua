import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SPREADSHEET_ID = "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw"
TAB_NAME = "RECETAS_BEBIDAS"

HEADERS = ["Bebida", "Ingrediente", "Cantidad", "Unidad", "Notas"]
RECIPES = [
    ["Cantaritos", "Reposado", "2", "oz", ""],
    ["Cantaritos", "Triple sec", "0.5", "oz", ""],
    ["Cantaritos", "Jugo de naranja", "2", "oz", ""],
    ["Cantaritos", "Jugo de limón", "1", "oz", ""],
    ["Cantaritos", "Agua gasificada limón Luna", "1", "oz", ""],
    ["Gin Tonic", "Gin", "2", "oz", "(usar José Cuervo si no hay Gin)"],
    ["Gin Tonic", "Agua gasificada limón Luna", "4", "oz", ""],
    ["Sangria Copa", "Vino tinto Tavernello", "5", "oz", ""],
    ["Sangria 1 Lt Jarra", "Vino tinto Tavernello", "16", "oz", ""],
    ["Sangria 1 Lt Jarra", "Jugo de naranja", "4", "oz", ""],
    ["Limonada Clásica", "Limonada clásica", "8", "oz", "concentrado en galones"],
    ["Limonada de Fresa", "Limonada de fresa", "8", "oz", ""],
    ["Infusion de Jamaica", "Jamaica", "8", "oz", ""],
    ["Te Especial de la Casa", "Té de limón", "8", "oz", ""],
    ["Guayaba", "Jugo de guayaba", "8", "oz", ""],
    ["Shot de Michelada", "Toña", "12", "oz", ""],
    ["Mix Chelada", "Toña", "12", "oz", ""],
    ["Chelada", "Victoria", "12", "oz", ""],
]
NOTE_TEXT = "1 galón = 128 oz | 1 botella estándar licor = 750ml = 25.4 oz"

_session = requests.Session()
_session.trust_env = False


def _hex_to_rgb(hex_color: str) -> dict:
    h = hex_color.strip().lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0,
    }


def _find_token_path() -> Path:
    env_path = os.getenv("SHEETS_TOKEN_PATH", "").strip()
    candidates = [
        Path(env_path) if env_path else None,
        Path("/app/token.json"),
        ROOT / "token.json",
        Path.cwd() / "token.json",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise RuntimeError("No se encontró token.json")


def _get_access_token() -> str:
    token_path = _find_token_path()
    data = json.loads(token_path.read_text(encoding="utf-8"))

    if data.get("token") and data.get("expiry"):
        try:
            expiry = datetime.fromisoformat(data["expiry"].replace("Z", "+00:00"))
            if expiry > datetime.now(timezone.utc) + timedelta(seconds=60):
                return data["token"]
        except Exception:
            pass

    required = ["token_uri", "client_id", "client_secret", "refresh_token"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise RuntimeError(f"token.json incompleto. Faltan campos: {', '.join(missing)}")

    resp = _session.post(
        data["token_uri"],
        data={
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    resp.raise_for_status()
    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Google token refresh no devolvió access_token")

    data["token"] = access_token
    expires_in = int(payload.get("expires_in", 3600))
    data["expiry"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return access_token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _get_metadata(spreadsheet_id: str) -> dict:
    r = _session.get(f"{BASE_URL}/{spreadsheet_id}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _batch_update(spreadsheet_id: str, requests_payload: list[dict]) -> dict:
    r = _session.post(
        f"{BASE_URL}/{spreadsheet_id}:batchUpdate",
        headers=_headers(),
        json={"requests": requests_payload},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _put_values(spreadsheet_id: str, range_a1: str, values: list[list[str]]) -> dict:
    r = _session.put(
        f"{BASE_URL}/{spreadsheet_id}/values/{range_a1}",
        headers=_headers(),
        params={"valueInputOption": "USER_ENTERED"},
        json={"range": range_a1, "majorDimension": "ROWS", "values": values},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _step_1_delete_tabs(spreadsheet_id: str, sheets: list[dict]) -> None:
    targets = {"INVENTARIO", "VENTAS_DIARIAS", "RECETAS"}
    delete_reqs = []
    for s in sheets:
        props = s.get("properties", {})
        title = props.get("title", "")
        if title in targets:
            delete_reqs.append({"deleteSheet": {"sheetId": props["sheetId"]}})

    if delete_reqs:
        _batch_update(spreadsheet_id, delete_reqs)
    print("STEP 1 — Deleted tabs (if existed):")
    for t in sorted(targets):
        print(f"- {t}")


def _ensure_recetas_tab(spreadsheet_id: str, sheets: list[dict]) -> int:
    for s in sheets:
        props = s.get("properties", {})
        if props.get("title") == TAB_NAME:
            return props["sheetId"]

    result = _batch_update(spreadsheet_id, [{"addSheet": {"properties": {"title": TAB_NAME}}}])
    replies = result.get("replies", [])
    if not replies:
        raise RuntimeError("No se pudo crear RECETAS_BEBIDAS")
    return replies[0]["addSheet"]["properties"]["sheetId"]


def _apply_formatting(spreadsheet_id: str, sheet_id: int, total_rows: int) -> None:
    dark_teal = _hex_to_rgb("#1B5E63")
    white = _hex_to_rgb("#FFFFFF")
    light_a = _hex_to_rgb("#F2FAFA")
    light_b = _hex_to_rgb("#E9F4F5")

    reqs = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 180},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 180},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
                "properties": {"pixelSize": 80},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4},
                "properties": {"pixelSize": 70},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5},
                "properties": {"pixelSize": 200},
                "fields": "pixelSize",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": dark_teal,
                        "textFormat": {"foregroundColor": white, "bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": total_rows, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                "fields": "userEnteredFormat.wrapStrategy",
            }
        },
    ]

    current = 1
    use_a = True
    i = 0
    while i < len(RECIPES):
        bebida = RECIPES[i][0]
        start = i
        while i < len(RECIPES) and RECIPES[i][0] == bebida:
            i += 1
        end = i
        color = light_a if use_a else light_b
        reqs.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": current + start,
                        "endRowIndex": current + end,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": color}},
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        )
        use_a = not use_a

    _batch_update(spreadsheet_id, reqs)


def _step_2_create_and_fill(spreadsheet_id: str) -> None:
    metadata = _get_metadata(spreadsheet_id)
    sheets = metadata.get("sheets", [])
    sheet_id = _ensure_recetas_tab(spreadsheet_id, sheets)

    values = [HEADERS] + RECIPES + [["", "", "", "", ""], [NOTE_TEXT, "", "", "", ""]]
    _put_values(spreadsheet_id, f"{TAB_NAME}!A1:E{len(values)}", values)
    _apply_formatting(spreadsheet_id, sheet_id, len(values))

    print("\nSTEP 2 — RECETAS_BEBIDAS created/populated/formatted")
    print(f"- Rows written: {len(values)}")


def _step_3_propose_tabs() -> None:
    print("\nSTEP 3 — Tabs to keep (proposal only):")
    print("- EMPLEADOS: Keep. Needed for staffing, schedule, roles, and labor coordination.")
    print("- EVENTOS_CALENDARIO: Keep. Needed for forecasting demand and operational planning by date/event.")
    print("- INSUMOS: Keep. Core for inventory inputs, purchases, and stock control used by Bruno.")


def _step_4_print_inventory(spreadsheet_id: str) -> None:
    metadata = _get_metadata(spreadsheet_id)
    names = [s.get("properties", {}).get("title", "") for s in metadata.get("sheets", [])]
    print("\nSTEP 4 — Final sheet inventory:")
    for name in names:
        print(f"- {name}")


def main() -> None:
    metadata = _get_metadata(SPREADSHEET_ID)
    _step_1_delete_tabs(SPREADSHEET_ID, metadata.get("sheets", []))
    _step_2_create_and_fill(SPREADSHEET_ID)
    _step_3_propose_tabs()
    _step_4_print_inventory(SPREADSHEET_ID)


if __name__ == "__main__":
    main()
