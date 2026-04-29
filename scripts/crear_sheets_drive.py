import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SOURCE_SHEET_ID = "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw"
HEADER_HEX = "#1B5E63"

_session = requests.Session()
_session.trust_env = False


def _find_token_path() -> Path:
    env_path = os.getenv("SHEETS_TOKEN_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    candidates = [
        ROOT / "token.json",
        Path("/app/token.json"),
        Path.cwd() / "token.json",
    ]
    for p in candidates:
        if p.exists():
            return p

    raise RuntimeError("No se encontro token.json (ROOT/token.json ni /app/token.json).")


def _get_access_token() -> str:
    token_path = _find_token_path()
    data = json.loads(token_path.read_text(encoding="utf-8"))

    expiry_raw = data.get("expiry")
    if data.get("token") and expiry_raw:
        try:
            expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            if expiry - datetime.now(timezone.utc) > timedelta(seconds=60):
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
    refreshed = resp.json()

    access_token = refreshed.get("access_token")
    if not access_token:
        raise RuntimeError("No se recibio access_token al refrescar token de Google.")

    data["token"] = access_token
    expires_in = int(refreshed.get("expires_in", 3600))
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    data["expiry"] = new_expiry.strftime("%Y-%m-%dT%H:%M:%SZ")
    token_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return access_token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _sheets_get(path: str, params: dict | None = None) -> dict:
    resp = _session.get(f"{SHEETS_BASE_URL}{path}", headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _sheets_put(path: str, body: dict, params: dict | None = None) -> dict:
    resp = _session.put(f"{SHEETS_BASE_URL}{path}", headers=_headers(), params=params, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _sheets_post(path: str, body: dict, params: dict | None = None) -> dict:
    resp = _session.post(f"{SHEETS_BASE_URL}{path}", headers=_headers(), params=params, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _create_spreadsheet(title: str) -> str:
    resp = _sheets_post("", {"properties": {"title": title}})
    return resp["spreadsheetId"]


def _sheet_metadata(spreadsheet_id: str) -> dict:
    return _sheets_get(f"/{spreadsheet_id}")


def _first_sheet_id(meta: dict) -> int:
    sheets = meta.get("sheets", [])
    if not sheets:
        raise RuntimeError("Spreadsheet sin tabs.")
    return sheets[0].get("properties", {}).get("sheetId")


def _find_sheet_props(meta: dict, title: str) -> dict | None:
    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if props.get("title") == title:
            return props
    return None


def _rename_sheet(spreadsheet_id: str, sheet_id: int, new_title: str) -> None:
    _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "title": new_title},
                        "fields": "title",
                    }
                }
            ]
        },
    )


def _add_sheet(spreadsheet_id: str, title: str) -> int:
    resp = _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {"requests": [{"addSheet": {"properties": {"title": title}}}]},
    )
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def _get_values(spreadsheet_id: str, a1_range: str) -> list[list[str]]:
    data = _sheets_get(f"/{spreadsheet_id}/values/{a1_range}")
    return data.get("values", [])


def _put_values(spreadsheet_id: str, a1_range: str, values: list[list[object]]) -> None:
    _sheets_put(
        f"/{spreadsheet_id}/values/{a1_range}",
        {"range": a1_range, "majorDimension": "ROWS", "values": values},
        params={"valueInputOption": "USER_ENTERED"},
    )


def _hex_to_rgb(hex_color: str) -> dict:
    c = hex_color.lstrip("#")
    return {
        "red": int(c[0:2], 16) / 255.0,
        "green": int(c[2:4], 16) / 255.0,
        "blue": int(c[4:6], 16) / 255.0,
    }


def _format_header(spreadsheet_id: str, tab_name: str, columns: int) -> None:
    if columns <= 0:
        return
    meta = _sheet_metadata(spreadsheet_id)
    props = _find_sheet_props(meta, tab_name)
    if not props:
        return

    _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": props["sheetId"],
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": columns,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": _hex_to_rgb(HEADER_HEX),
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            ]
        },
    )


def _set_column_widths(spreadsheet_id: str, tab_name: str, widths: list[int]) -> None:
    meta = _sheet_metadata(spreadsheet_id)
    props = _find_sheet_props(meta, tab_name)
    if not props:
        return

    requests = []
    for idx, width in enumerate(widths):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": props["sheetId"],
                        "dimension": "COLUMNS",
                        "startIndex": idx,
                        "endIndex": idx + 1,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )

    if requests:
        _sheets_post(f"/{spreadsheet_id}:batchUpdate", {"requests": requests})


def _delete_sheet_if_exists(spreadsheet_id: str, title: str) -> bool:
    meta = _sheet_metadata(spreadsheet_id)
    props = _find_sheet_props(meta, title)
    if not props:
        return False
    _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {"requests": [{"deleteSheet": {"sheetId": props["sheetId"]}}]},
    )
    return True


def _update_env(sheet_ids: dict[str, str]) -> None:
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()

    new_entries = [
        f"SHEETS_ID_BEBIDAS={SOURCE_SHEET_ID}",
        f"SHEETS_ID_ADMIN={sheet_ids['admin']}",
        f"SHEETS_ID_CONFIG={sheet_ids['config']}",
        f"SHEETS_ID_PERSONAL={sheet_ids['personal']}",
        f"SHEETS_ID_AGENDA={sheet_ids['agenda']}",
    ]

    filtered = []
    keys_to_remove = {
        "SHEETS_ID_BEBIDAS",
        "SHEETS_ID_ADMIN",
        "SHEETS_ID_CONFIG",
        "SHEETS_ID_PERSONAL",
        "SHEETS_ID_AGENDA",
    }
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            filtered.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in keys_to_remove:
            continue
        filtered.append(line)

    out = []
    inserted = False
    for line in filtered:
        out.append(line)
        if line.strip().startswith("GOOGLE_SHEETS_ID=") and not inserted:
            out.extend(new_entries)
            inserted = True

    if not inserted:
        out.extend(new_entries)

    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    # STEP 1
    proveedores = _get_values(SOURCE_SHEET_ID, "PROVEEDORES!A:E")
    postres = _get_values(SOURCE_SHEET_ID, "POSTRES!A:D")
    catalogo = _get_values(SOURCE_SHEET_ID, "CATALOGO_LICORES!A:H")
    recetas = _get_values(SOURCE_SHEET_ID, "RECETAS_BEBIDAS!A:E")

    # STEP 2
    admin_id = _create_spreadsheet("Casa Antigua - Administracion")
    config_id = _create_spreadsheet("Casa Antigua - Configuracion")
    personal_id = _create_spreadsheet("Casa Antigua - Personal")
    agenda_id = _create_spreadsheet("Casa Antigua - Agenda")

    # STEP 3A - Administracion
    meta = _sheet_metadata(admin_id)
    _rename_sheet(admin_id, _first_sheet_id(meta), "PROVEEDORES")
    if proveedores:
        _put_values(admin_id, "PROVEEDORES!A:E", proveedores)
        _format_header(admin_id, "PROVEEDORES", 5)
    _add_sheet(admin_id, "POSTRES")
    if postres:
        _put_values(admin_id, "POSTRES!A:D", postres)
        _format_header(admin_id, "POSTRES", 4)

    # STEP 3B - Configuracion
    meta = _sheet_metadata(config_id)
    _rename_sheet(config_id, _first_sheet_id(meta), "CATALOGO_LICORES")
    if catalogo:
        _put_values(config_id, "CATALOGO_LICORES!A:H", catalogo)
        _format_header(config_id, "CATALOGO_LICORES", 8)
    _add_sheet(config_id, "RECETAS_BEBIDAS")
    if recetas:
        _put_values(config_id, "RECETAS_BEBIDAS!A:E", recetas)
        _format_header(config_id, "RECETAS_BEBIDAS", 5)

    # STEP 3C - Personal
    meta = _sheet_metadata(personal_id)
    _rename_sheet(personal_id, _first_sheet_id(meta), "EMPLEADOS")
    empleados_values = [
        ["Nombre", "Cargo", "Telefono", "Turno", "Fecha_inicio", "Estado", "Notas"],
        ["Flor", "Supervisora", "+505-XXXX-XXXX", "Mañana/Tarde", "01/01/2026", "Activo", ""],
        ["Jean", "Bartender", "+505-XXXX-XXXX", "Tarde/Noche", "01/01/2026", "Activo", ""],
        ["Jorge", "Mesero", "+505-XXXX-XXXX", "Tarde/Noche", "01/01/2026", "Activo", ""],
    ]
    _put_values(personal_id, "EMPLEADOS!A:G", empleados_values)
    _format_header(personal_id, "EMPLEADOS", 7)

    # STEP 3D - Agenda
    meta = _sheet_metadata(agenda_id)
    _rename_sheet(agenda_id, _first_sheet_id(meta), "EVENTOS_CALENDARIO")
    agenda_headers = [["Fecha", "Evento", "Tipo", "Capacidad", "Responsable", "Estado", "Notas"]]
    _put_values(agenda_id, "EVENTOS_CALENDARIO!A:G", agenda_headers)
    _format_header(agenda_id, "EVENTOS_CALENDARIO", 7)
    _set_column_widths(agenda_id, "EVENTOS_CALENDARIO", [100, 200, 120, 90, 120, 100, 200])

    # STEP 4
    for tab in [
        "PROVEEDORES",
        "POSTRES",
        "CATALOGO_LICORES",
        "RECETAS_BEBIDAS",
        "EMPLEADOS",
        "EVENTOS_CALENDARIO",
        "INSUMOS",
    ]:
        _delete_sheet_if_exists(SOURCE_SHEET_ID, tab)

    # STEP 5
    ids = {
        "admin": admin_id,
        "config": config_id,
        "personal": personal_id,
        "agenda": agenda_id,
    }
    _update_env(ids)

    # STEP 6
    print("[OK] Sheets creados:\n")

    print("📊 Casa Antigua - Administracion")
    print(f"   ID: {admin_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{admin_id}")
    print("   Tabs: PROVEEDORES, POSTRES\n")

    print("📊 Casa Antigua - Configuracion")
    print(f"   ID: {config_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{config_id}")
    print("   Tabs: CATALOGO_LICORES, RECETAS_BEBIDAS\n")

    print("📊 Casa Antigua - Personal")
    print(f"   ID: {personal_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{personal_id}")
    print("   Tabs: EMPLEADOS\n")

    print("📊 Casa Antigua - Agenda")
    print(f"   ID: {agenda_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{agenda_id}")
    print("   Tabs: EVENTOS_CALENDARIO\n")

    print("📊 Bebidas_Inventario (original - limpiado)")
    print(f"   ID: {SOURCE_SHEET_ID}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{SOURCE_SHEET_ID}")
    print("   Tabs restantes: INVENTARIO_BEBIDAS, ENTRADAS\n")

    print("[OK] .env actualizado")
    print("[INFO] Para organizar en carpetas: ir a drive.google.com, crear carpeta \"Casa Antigua\" y mover los 5 Sheets manualmente.")


if __name__ == "__main__":
    main()

