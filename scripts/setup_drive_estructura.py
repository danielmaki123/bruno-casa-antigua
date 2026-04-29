import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests import HTTPError

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3"
SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SOURCE_SHEET_ID = "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw"
HEADER_HEX = "#1B5E63"

_session = requests.Session()
_session.trust_env = False


def _find_token_path() -> Path:
    env_path = os.getenv("SHEETS_TOKEN_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    root_token = ROOT / "token.json"
    if root_token.exists():
        return root_token

    docker_token = Path("/app/token.json")
    if docker_token.exists():
        return docker_token

    cwd_token = Path.cwd() / "token.json"
    if cwd_token.exists():
        return cwd_token

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


def _drive_get(path: str, params: dict | None = None) -> dict:
    merged = {"supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
    if params:
        merged.update(params)
    resp = _session.get(f"{DRIVE_BASE_URL}{path}", headers=_headers(), params=merged, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _drive_post(path: str, body: dict, params: dict | None = None) -> dict:
    merged = {"supportsAllDrives": "true"}
    if params:
        merged.update(params)
    resp = _session.post(f"{DRIVE_BASE_URL}{path}", headers=_headers(), params=merged, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _drive_patch(path: str, body: dict, params: dict | None = None) -> dict:
    merged = {"supportsAllDrives": "true"}
    if params:
        merged.update(params)
    resp = _session.patch(f"{DRIVE_BASE_URL}{path}", headers=_headers(), params=merged, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


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


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _find_folder(name: str, parent_id: str | None) -> dict | None:
    parent_clause = "'root' in parents" if parent_id is None else f"'{parent_id}' in parents"
    q = (
        f"name='{_escape_drive_query(name)}' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false and "
        f"{parent_clause}"
    )
    data = _drive_get("/files", params={"q": q, "fields": "files(id,name,parents)"})
    files = data.get("files", [])
    return files[0] if files else None


def _get_or_create_folder(name: str, parent_id: str | None) -> str:
    existing = _find_folder(name, parent_id)
    if existing:
        return existing["id"]

    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    created = _drive_post("/files", body, params={"fields": "id,name"})
    return created["id"]


def _find_spreadsheet(name: str, parent_id: str) -> dict | None:
    q = (
        f"name='{_escape_drive_query(name)}' and "
        "mimeType='application/vnd.google-apps.spreadsheet' and "
        "trashed=false and "
        f"'{parent_id}' in parents"
    )
    data = _drive_get("/files", params={"q": q, "fields": "files(id,name,parents)"})
    files = data.get("files", [])
    return files[0] if files else None


def _get_or_create_spreadsheet(name: str, parent_id: str) -> str:
    existing = _find_spreadsheet(name, parent_id)
    if existing:
        return existing["id"]
    created = _drive_post(
        "/files",
        {"name": name, "mimeType": "application/vnd.google-apps.spreadsheet", "parents": [parent_id]},
        params={"fields": "id,name"},
    )
    return created["id"]


def _sheet_metadata(spreadsheet_id: str) -> dict:
    return _sheets_get(f"/{spreadsheet_id}")


def _find_sheet(meta: dict, title: str) -> dict | None:
    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if props.get("title") == title:
            return s
    return None


def _add_sheet(spreadsheet_id: str, title: str) -> int:
    resp = _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {"requests": [{"addSheet": {"properties": {"title": title}}}]},
    )
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def _ensure_sheet(spreadsheet_id: str, title: str) -> int:
    meta = _sheet_metadata(spreadsheet_id)
    found = _find_sheet(meta, title)
    if found:
        return found["properties"]["sheetId"]
    return _add_sheet(spreadsheet_id, title)


def _delete_sheet_if_exists(spreadsheet_id: str, title: str) -> None:
    meta = _sheet_metadata(spreadsheet_id)
    found = _find_sheet(meta, title)
    if not found:
        return
    sheet_id = found["properties"]["sheetId"]
    _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {"requests": [{"deleteSheet": {"sheetId": sheet_id}}]},
    )


def _get_values(spreadsheet_id: str, tab_name: str, value_range: str = "A:ZZ") -> list[list[str]]:
    data = _sheets_get(f"/{spreadsheet_id}/values/{tab_name}!{value_range}")
    return data.get("values", [])


def _put_values(spreadsheet_id: str, tab_name: str, values: list[list[object]]) -> None:
    if not values:
        return
    _sheets_put(
        f"/{spreadsheet_id}/values/{tab_name}!A1",
        {"range": f"{tab_name}!A1", "majorDimension": "ROWS", "values": values},
        params={"valueInputOption": "USER_ENTERED"},
    )


def _hex_to_rgb(hex_color: str) -> dict:
    c = hex_color.lstrip("#")
    if len(c) != 6:
        raise ValueError(f"Color invalido: {hex_color}")
    return {
        "red": int(c[0:2], 16) / 255.0,
        "green": int(c[2:4], 16) / 255.0,
        "blue": int(c[4:6], 16) / 255.0,
    }


def _format_header(spreadsheet_id: str, tab_name: str, columns: int) -> None:
    if columns <= 0:
        return
    meta = _sheet_metadata(spreadsheet_id)
    found = _find_sheet(meta, tab_name)
    if not found:
        return
    sheet_id = found["properties"]["sheetId"]
    _sheets_post(
        f"/{spreadsheet_id}:batchUpdate",
        {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": columns,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": _hex_to_rgb(HEADER_HEX),
                                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                }
            ]
        },
    )


def _copy_tab(source_sheet_id: str, source_tab: str, target_sheet_id: str, target_tab: str) -> None:
    _ensure_sheet(target_sheet_id, target_tab)
    values = _get_values(source_sheet_id, source_tab, "A:ZZ")
    if values:
        _put_values(target_sheet_id, target_tab, values)
        _format_header(target_sheet_id, target_tab, len(values[0]))


def _set_headers_tab(sheet_id: str, tab_name: str, headers: list[str]) -> None:
    _ensure_sheet(sheet_id, tab_name)
    _put_values(sheet_id, tab_name, [headers])
    _format_header(sheet_id, tab_name, len(headers))


def _cleanup_original_sheet() -> None:
    to_delete = [
        "PROVEEDORES",
        "POSTRES",
        "CATALOGO_LICORES",
        "RECETAS_BEBIDAS",
        "EMPLEADOS",
        "EVENTOS_CALENDARIO",
        "INSUMOS",
    ]
    for tab in to_delete:
        _delete_sheet_if_exists(SOURCE_SHEET_ID, tab)


def _update_env_values(values: dict[str, str]) -> None:
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()
    existing = {}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        existing[key] = i

    for key, val in values.items():
        new_line = f"{key}={val}"
        if key in existing:
            lines[existing[key]] = new_line
        else:
            lines.append(new_line)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    casa_id = _get_or_create_folder("Casa Antigua", None)
    operaciones_id = _get_or_create_folder("Operaciones", casa_id)
    administracion_folder_id = _get_or_create_folder("Administracion", casa_id)
    configuracion_folder_id = _get_or_create_folder("Configuracion", casa_id)
    personal_folder_id = _get_or_create_folder("Personal", casa_id)
    agenda_folder_id = _get_or_create_folder("Agenda", casa_id)

    try:
        src_meta = _drive_get(f"/files/{SOURCE_SHEET_ID}", params={"fields": "id,name,parents"})
    except HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise RuntimeError(
                "Drive API no puede acceder al spreadsheet origen (404). "
                "El token actual probablemente no incluye scope de Drive o no tiene permiso sobre ese archivo."
            ) from exc
        raise
    parent_ids = src_meta.get("parents", [])
    remove_parents = "root" if "root" in parent_ids else ",".join(parent_ids)
    if not remove_parents:
        remove_parents = "root"

    _drive_patch(
        f"/files/{SOURCE_SHEET_ID}",
        {"name": "Bebidas_Inventario"},
        params={
            "addParents": operaciones_id,
            "removeParents": remove_parents,
            "fields": "id,name,parents",
        },
    )

    admin_sheet_id = _get_or_create_spreadsheet("Administracion", administracion_folder_id)
    _copy_tab(SOURCE_SHEET_ID, "PROVEEDORES", admin_sheet_id, "PROVEEDORES")
    _copy_tab(SOURCE_SHEET_ID, "POSTRES", admin_sheet_id, "POSTRES")
    _delete_sheet_if_exists(admin_sheet_id, "Sheet1")

    config_sheet_id = _get_or_create_spreadsheet("Configuracion", configuracion_folder_id)
    _copy_tab(SOURCE_SHEET_ID, "CATALOGO_LICORES", config_sheet_id, "CATALOGO_LICORES")
    _copy_tab(SOURCE_SHEET_ID, "RECETAS_BEBIDAS", config_sheet_id, "RECETAS_BEBIDAS")
    _delete_sheet_if_exists(config_sheet_id, "Sheet1")

    personal_sheet_id = _get_or_create_spreadsheet("Personal", personal_folder_id)
    _set_headers_tab(
        personal_sheet_id,
        "EMPLEADOS",
        ["Nombre", "Cargo", "Telefono", "Turno", "Fecha_inicio", "Estado", "Notas"],
    )
    _delete_sheet_if_exists(personal_sheet_id, "Sheet1")

    agenda_sheet_id = _get_or_create_spreadsheet("Agenda", agenda_folder_id)
    _set_headers_tab(
        agenda_sheet_id,
        "EVENTOS_CALENDARIO",
        ["Fecha", "Evento", "Tipo", "Capacidad", "Responsable", "Estado", "Notas"],
    )
    _delete_sheet_if_exists(agenda_sheet_id, "Sheet1")

    _cleanup_original_sheet()

    _update_env_values(
        {
            "SHEETS_ID_BEBIDAS": SOURCE_SHEET_ID,
            "SHEETS_ID_ADMIN": admin_sheet_id,
            "SHEETS_ID_CONFIG": config_sheet_id,
            "SHEETS_ID_PERSONAL": personal_sheet_id,
            "SHEETS_ID_AGENDA": agenda_sheet_id,
            "GOOGLE_SHEETS_ID": SOURCE_SHEET_ID,
        }
    )

    print("[OK] Carpetas Drive creadas:")
    print("  Casa Antigua/")
    print(f"  ├── Operaciones/     → Bebidas_Inventario (ID: {SOURCE_SHEET_ID})")
    print(f"  ├── Administracion/  → Administracion (ID: {admin_sheet_id})")
    print(f"  ├── Configuracion/   → Configuracion (ID: {config_sheet_id})")
    print(f"  ├── Personal/        → Personal (ID: {personal_sheet_id})")
    print(f"  └── Agenda/          → Agenda (ID: {agenda_sheet_id})")
    print("[OK] .env actualizado con nuevos Sheet IDs")
    print("[OK] inventario_monitor.py actualizado")
    print("[URL] https://drive.google.com/drive/folders/" + casa_id)


if __name__ == "__main__":
    main()
