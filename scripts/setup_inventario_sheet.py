import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SHEET_INVENTARIO = "INVENTARIO_BEBIDAS"
SHEET_PROVEEDORES = "PROVEEDORES"
SHEET_POSTRES = "POSTRES"

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


def _spreadsheet_id() -> str:
    sid = os.getenv("GOOGLE_SHEETS_ID")
    if not sid:
        raise RuntimeError("GOOGLE_SHEETS_ID no esta configurado en .env")
    return sid


def _col_to_a1(col_index: int) -> str:
    out = ""
    n = col_index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _get_spreadsheet_metadata(spreadsheet_id: str) -> dict:
    url = f"{BASE_URL}/{spreadsheet_id}"
    resp = _session.get(url, headers=_headers(), timeout=25)
    resp.raise_for_status()
    return resp.json()


def _get_values(spreadsheet_id: str, range_a1: str) -> list[list[str]]:
    url = f"{BASE_URL}/{spreadsheet_id}/values/{range_a1}"
    resp = _session.get(url, headers=_headers(), timeout=25)
    resp.raise_for_status()
    return resp.json().get("values", [])


def _batch_add_sheets_if_missing(spreadsheet_id: str, required_names: list[str], existing_names: set[str]) -> list[str]:
    missing = [name for name in required_names if name not in existing_names]
    if not missing:
        return []

    requests_body = {
        "requests": [{"addSheet": {"properties": {"title": name}}} for name in missing]
    }
    url = f"{BASE_URL}/{spreadsheet_id}:batchUpdate"
    resp = _session.post(url, headers=_headers(), json=requests_body, timeout=25)
    resp.raise_for_status()
    return missing


def _update_values(spreadsheet_id: str, range_a1: str, values: list[list[object]]) -> dict:
    url = f"{BASE_URL}/{spreadsheet_id}/values/{range_a1}"
    resp = _session.put(
        url,
        headers=_headers(),
        params={"valueInputOption": "USER_ENTERED"},
        json={"range": range_a1, "majorDimension": "ROWS", "values": values},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()


def _build_inventory_catalog() -> list[list[object]]:
    rows: list[list[object]] = []

    def add_group(categoria: str, unidad: str, stock_min: float, proveedor_id: int, productos: list[str]) -> None:
        for nombre in productos:
            rows.append([nombre, categoria, unidad, stock_min, proveedor_id])

    add_group(
        "Gaseosas",
        "unidades",
        24,
        1,
        [
            "Toña",
            "Victoria",
            "Coca regular",
            "Coca cero",
            "Fanta naranja",
            "Fanta roja",
            "Fanta uva",
            "Fresca",
            "Canada Dry",
            "Agua purificada",
            "Agua gasificada limón Luna",
            "Agua gasificada fresa Luna",
        ],
    )
    add_group(
        "Cervezas",
        "unidades",
        12,
        1,
        [
            "Heineken",
            "Miller",
            "Sol",
            "Toña Lite",
            "Toña Ultra",
            "Victoria Frost",
            "Boreal",
            "Santiago Apóstol",
            "Guardabarranco",
            "Kaori",
        ],
    )
    add_group(
        "Hard Seltzer",
        "unidades",
        6,
        1,
        [
            "Hard Limón",
            "Hard Raspberry",
            "Seltzer Grapefruit",
            "Seltzer Sandia",
            "Seltzer Trop Berry",
        ],
    )
    add_group(
        "Licores y Vinos",
        "botellas",
        0.5,
        2,
        [
            "Flor de Caña 12",
            "Flor de Caña 18",
            "Flor de Caña Gran Reserva",
            "Extra Lite litro",
            "Extra Lite 1/2",
            "José Cuervo",
            "Jarana",
            "Reposado",
            "Vodkalla",
            "Triple sec",
            "Vino tinto Tavernello",
            "Undurraga",
            "Viña Esmeralda",
            "Aliwen",
            "Luis Felipe",
            "Espumoso rosé",
            "Aperol",
            "Granadine",
        ],
    )
    add_group(
        "Jugos",
        "galones",
        1.0,
        3,
        [
            "Jugo de guayaba",
            "Jugo de naranja",
            "Jugo de limón",
            "Limonada clásica",
            "Limonada de fresa",
            "Té de limón",
            "Jamaica",
            "Toronja",
            "Concentrado de limón",
            "Concentrado de mango",
            "Concentrado de guayaba",
        ],
    )
    add_group(
        "Postres",
        "porciones",
        3,
        4,
        [
            "Flan",
            "Red velvet",
            "Torta alemana",
            "Pastel de zanahoria",
            "Cheesecake de limón",
            "Tres leches",
        ],
    )
    return rows


def _build_proveedores_rows() -> list[list[object]]:
    return [
        [1, "Proveedor Bebidas", "", "miercoles", "Gaseosas y cervezas"],
        [2, "Proveedor Licores", "", "miercoles", "Licores"],
        [3, "Proveedor Jugos", "", "miercoles", "Jugos"],
        [4, "Proveedor Postres", "", "lunes", "Postres"],
    ]


def _build_postres_rows() -> list[list[object]]:
    return [
        ["Flan", 5],
        ["Red velvet", 3],
        ["Torta alemana", 3],
        ["Pastel de zanahoria", 5],
        ["Cheesecake de limón", 3],
        ["Tres leches", 3],
    ]


def _build_inventory_values(spreadsheet_id: str) -> list[list[object]]:
    existing_header_row = _get_values(spreadsheet_id, f"{SHEET_INVENTARIO}!1:1")
    existing_headers = existing_header_row[0] if existing_header_row else []
    existing_dates = [str(h).strip() for h in existing_headers[5:] if str(h).strip()]

    today = datetime.now().strftime("%d/%m/%Y")
    ordered_dates = [today] + [d for d in existing_dates if d != today]

    header = ["Producto", "Categoria", "Unidad", "Stock Min", "Proveedor ID"] + ordered_dates
    catalog_rows = _build_inventory_catalog()
    blanks = [[""] * len(ordered_dates) for _ in catalog_rows]
    return [header] + [base + extra for base, extra in zip(catalog_rows, blanks)]


def main() -> None:
    spreadsheet_id = _spreadsheet_id()
    metadata = _get_spreadsheet_metadata(spreadsheet_id)
    existing_names = {
        s.get("properties", {}).get("title", "")
        for s in metadata.get("sheets", [])
    }

    created = _batch_add_sheets_if_missing(
        spreadsheet_id,
        [SHEET_INVENTARIO, SHEET_PROVEEDORES, SHEET_POSTRES],
        existing_names,
    )

    inventory_values = _build_inventory_values(spreadsheet_id)
    providers_values = [["Proveedor ID", "Nombre", "Telefono", "Dia Pedido", "Categoria"]] + _build_proveedores_rows()
    desserts_values = [["Postre", "Stock Min"]] + _build_postres_rows()

    inv_last_col = _col_to_a1(len(inventory_values[0]))
    inv_last_row = len(inventory_values)
    prov_last_row = len(providers_values)
    des_last_row = len(desserts_values)

    inv_result = _update_values(
        spreadsheet_id,
        f"{SHEET_INVENTARIO}!A1:{inv_last_col}{inv_last_row}",
        inventory_values,
    )
    prov_result = _update_values(
        spreadsheet_id,
        f"{SHEET_PROVEEDORES}!A1:E{prov_last_row}",
        providers_values,
    )
    des_result = _update_values(
        spreadsheet_id,
        f"{SHEET_POSTRES}!A1:B{des_last_row}",
        desserts_values,
    )

    print("=== setup_inventario_sheet summary ===")
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheets creadas: {created if created else 'ninguna (ya existian)'}")
    print(f"{SHEET_INVENTARIO}: {inv_result.get('updatedRows', 0)} filas, {inv_result.get('updatedCells', 0)} celdas")
    print(f"{SHEET_PROVEEDORES}: {prov_result.get('updatedRows', 0)} filas, {prov_result.get('updatedCells', 0)} celdas")
    print(f"{SHEET_POSTRES}: {des_result.get('updatedRows', 0)} filas, {des_result.get('updatedCells', 0)} celdas")


if __name__ == "__main__":
    main()
