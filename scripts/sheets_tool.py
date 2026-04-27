import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("sheets_tool")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _normalize_key(value: str) -> str:
    value = value or ""
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
    }
    result = value.strip().lower()
    for source, target in replacements.items():
        result = result.replace(source, target)
    result = re.sub(r"[^a-z0-9]+", "_", result)
    return result.strip("_")


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(" ", "")
    # 12.345,67 -> 12345.67 | 12345,67 -> 12345.67
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def _load_config() -> str:
    root = _project_root()
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_ID no está configurado en .env")
    return spreadsheet_id


def _build_service():
    token_path = _project_root() / "token.json"
    if not token_path.exists():
        raise RuntimeError(f"No se encontró token.json en {token_path}")

    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return build("sheets", "v4", credentials=credentials)


def _read_sheet(service, spreadsheet_id: str, sheet_name: str) -> List[Dict[str, Any]]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []

    headers = [str(col).strip() for col in values[0]]
    rows: List[Dict[str, Any]] = []
    for row_values in values[1:]:
        row: Dict[str, Any] = {}
        for idx, header in enumerate(headers):
            row[header] = row_values[idx] if idx < len(row_values) else ""
        rows.append(row)

    return rows


def _get_headers(service, spreadsheet_id: str, sheet_name: str) -> List[str]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!1:1")
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []
    return [str(col).strip() for col in values[0]]


def _append_row(service, spreadsheet_id: str, sheet_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = _get_headers(service, spreadsheet_id, sheet_name)

    if not headers:
        headers = list(payload.keys())
        if not headers:
            raise RuntimeError("--data no contiene campos para insertar")

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!1:1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

    row_values = [payload.get(header, "") for header in headers]

    append_result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]},
        )
        .execute()
    )

    updates = append_result.get("updates", {})
    return {
        "success": True,
        "sheet": sheet_name,
        "updatedRange": updates.get("updatedRange"),
        "updatedRows": updates.get("updatedRows", 0),
    }


def _find_value(row: Dict[str, Any], candidates: List[str]) -> Any:
    normalized_map = {_normalize_key(k): v for k, v in row.items()}
    for candidate in candidates:
        norm = _normalize_key(candidate)
        if norm in normalized_map:
            return normalized_map[norm]
    return None


def _get_stock_status(service, spreadsheet_id: str) -> Dict[str, Any]:
    insumos = _read_sheet(service, spreadsheet_id, "INSUMOS")
    inventario = _read_sheet(service, spreadsheet_id, "INVENTARIO")

    last_inventory_by_insumo: Dict[str, Dict[str, Any]] = {}
    for row in inventario:
        insumo_id_value = _find_value(row, ["insumo_id", "id_insumo", "codigo", "id"])
        if insumo_id_value is None:
            continue
        insumo_id = str(insumo_id_value).strip()
        if not insumo_id:
            continue
        last_inventory_by_insumo[insumo_id] = row

    status_rows: List[Dict[str, Any]] = []
    for item in insumos:
        insumo_id = str(_find_value(item, ["insumo_id", "id_insumo", "codigo", "id"]) or "").strip()
        nombre = _find_value(item, ["nombre", "insumo", "descripcion", "producto"]) or ""
        minimo = _to_float(_find_value(item, ["stock_min", "stock_minimo", "minimo", "min"]))
        critico = _to_float(_find_value(item, ["stock_critico", "critico", "nivel_critico", "critical"]))

        inventory_row = last_inventory_by_insumo.get(insumo_id)
        cantidad = None
        if inventory_row:
            cantidad = _to_float(
                _find_value(inventory_row, ["cantidad_fisica", "cantidad", "stock", "stock_actual"])
            )

        if cantidad is None:
            status = "critico"
        elif critico is not None and cantidad <= critico:
            status = "critico"
        elif minimo is not None and cantidad <= minimo:
            status = "bajo"
        else:
            status = "ok"

        status_rows.append(
            {
                "insumo_id": insumo_id,
                "nombre": nombre,
                "cantidad": cantidad,
                "stock_min": minimo,
                "stock_critico": critico,
                "status": status,
            }
        )

    return {"status": status_rows}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Puente Hermes <-> Google Sheets")
    parser.add_argument(
        "--action",
        required=True,
        choices=["read", "append", "get_stock_status"],
        help="Acción a ejecutar",
    )
    parser.add_argument("--sheet", help="Nombre de la hoja (obligatorio para read/append)")
    parser.add_argument("--data", help="JSON string con data a insertar (append)")
    args = parser.parse_args()

    try:
        spreadsheet_id = _load_config()
        service = _build_service()

        if args.action == "read":
            if not args.sheet:
                raise RuntimeError("--sheet es obligatorio para --action read")
            rows = _read_sheet(service, spreadsheet_id, args.sheet)
            _print_json(rows)
            return

        if args.action == "append":
            if not args.sheet:
                raise RuntimeError("--sheet es obligatorio para --action append")
            if not args.data:
                raise RuntimeError("--data es obligatorio para --action append")

            try:
                payload = json.loads(args.data)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"--data no es JSON válido: {exc}") from exc

            if not isinstance(payload, dict):
                raise RuntimeError("--data debe ser un JSON object")

            result = _append_row(service, spreadsheet_id, args.sheet, payload)
            _print_json(result)
            return

        if args.action == "get_stock_status":
            result = _get_stock_status(service, spreadsheet_id)
            _print_json(result)
            return

        raise RuntimeError(f"Acción no soportada: {args.action}")

    except Exception as exc:
        logger.exception("Error ejecutando sheets_tool")
        _print_json({"error": str(exc)})


if __name__ == "__main__":
    main()
