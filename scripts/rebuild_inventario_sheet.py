import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "").strip() or "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL_FALLBACK = "postgres://postgres:06c5f13aaaaa58a7f6f1@76.13.250.83:5435/brunobot?sslmode=disable"

SHEET_INVENTARIO = "INVENTARIO_BEBIDAS"
SHEET_CATALOGO = "CATALOGO_LICORES"
SHEET_RECETAS = "RECETAS_BEBIDAS"

_session = requests.Session()
_session.trust_env = False


def _hex_to_rgb(hex_color: str) -> dict:
    h = hex_color.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Color HEX invalido: {hex_color}")
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0,
    }


def _find_token_path() -> Path:
    env_path = os.getenv("SHEETS_TOKEN_PATH", "").strip()
    candidates = [
        Path(env_path) if env_path else None,
        ROOT / "token.json",
        Path("/app/token.json"),
        Path.cwd() / "token.json",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise RuntimeError("No se encontro token.json (ROOT/token.json ni /app/token.json).")


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
        raise RuntimeError("Google token refresh no devolvio access_token")

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


def _sheet_get() -> dict:
    r = _session.get(f"{BASE_URL}/{SPREADSHEET_ID}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _batch_update(requests_payload: list[dict]) -> dict:
    r = _session.post(
        f"{BASE_URL}/{SPREADSHEET_ID}:batchUpdate",
        headers=_headers(),
        json={"requests": requests_payload},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _values_get(range_a1: str) -> list[list[str]]:
    r = _session.get(f"{BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("values", [])


def _values_put(range_a1: str, values: list[list[object]]) -> None:
    r = _session.put(
        f"{BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}",
        headers=_headers(),
        params={"valueInputOption": "USER_ENTERED"},
        json={"range": range_a1, "majorDimension": "ROWS", "values": values},
        timeout=60,
    )
    r.raise_for_status()


def _values_clear(range_a1: str) -> None:
    r = _session.post(
        f"{BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}:clear",
        headers=_headers(),
        json={},
        timeout=30,
    )
    r.raise_for_status()


def _ensure_sheet(sheet_name: str) -> int:
    meta = _sheet_get()
    for s in meta.get("sheets", []):
        p = s.get("properties", {})
        if p.get("title") == sheet_name:
            return p["sheetId"]

    reply = _batch_update([{"addSheet": {"properties": {"title": sheet_name}}}])
    return reply["replies"][0]["addSheet"]["properties"]["sheetId"]


def _sheet_id_from_meta(meta: dict, sheet_name: str) -> int:
    for s in meta.get("sheets", []):
        p = s.get("properties", {})
        if p.get("title") == sheet_name:
            return p["sheetId"]
    raise RuntimeError(f"No existe la hoja {sheet_name}")


def _date_headers() -> list[str]:
    start = date(2026, 4, 27)
    end = date(2026, 12, 31)
    out = []
    cur = start
    while cur <= end:
        out.append(cur.strftime("%d/%m/%Y"))
        cur += timedelta(days=1)
    return out


def _build_catalog_rows() -> list[list[object]]:
    rows: list[list[object]] = []

    rows.extend([
        ["Toña", "Gaseosas y refrescos", "unidades", 24, 1],
        ["Victoria", "Gaseosas y refrescos", "unidades", 24, 1],
        ["Coca regular", "Gaseosas y refrescos", "unidades", 24, 1],
        ["Coca cero", "Gaseosas y refrescos", "unidades", 24, 1],
        ["Fanta naranja", "Gaseosas y refrescos", "unidades", 12, 1],
        ["Fanta roja", "Gaseosas y refrescos", "unidades", 12, 1],
        ["Fanta uva", "Gaseosas y refrescos", "unidades", 12, 1],
        ["Fresca", "Gaseosas y refrescos", "unidades", 12, 1],
        ["Canada Dry", "Gaseosas y refrescos", "unidades", 12, 1],
        ["Agua purificada", "Gaseosas y refrescos", "unidades", 24, 1],
        ["Agua gasificada limón Luna", "Gaseosas y refrescos", "unidades", 6, 1],
        ["Agua gasificada fresa Luna", "Gaseosas y refrescos", "unidades", 6, 1],
    ])

    rows.extend([
        ["Heineken", "Cervezas", "unidades", 12, 1],
        ["Miller", "Cervezas", "unidades", 12, 1],
        ["Sol", "Cervezas", "unidades", 12, 1],
        ["Toña Lite", "Cervezas", "unidades", 6, 1],
        ["Toña Ultra", "Cervezas", "unidades", 6, 1],
        ["Victoria Frost", "Cervezas", "unidades", 6, 1],
        ["Boreal", "Cervezas", "unidades", 6, 1],
        ["Santiago Apóstol", "Cervezas", "unidades", 6, 1],
        ["Guardabarranco", "Cervezas", "unidades", 6, 1],
        ["Kaori", "Cervezas", "unidades", 6, 1],
    ])

    rows.extend([
        ["Hard Limón", "Hard Seltzer", "unidades", 6, 1],
        ["Hard Raspberry", "Hard Seltzer", "unidades", 6, 1],
        ["Seltzer Grapefruit", "Hard Seltzer", "unidades", 6, 1],
        ["Seltzer Sandia", "Hard Seltzer", "unidades", 6, 1],
        ["Seltzer Trop Berry", "Hard Seltzer", "unidades", 6, 1],
    ])

    rows.extend([
        ["Flor de Caña 12", "Licores y Vinos", "gramos", 700, 2],
        ["Flor de Caña 18", "Licores y Vinos", "gramos", 700, 2],
        ["Flor de Caña Gran Reserva", "Licores y Vinos", "gramos", 700, 2],
        ["Extra Lite litro", "Licores y Vinos", "gramos", 820, 2],
        ["Extra Lite 1/2", "Licores y Vinos", "gramos", 450, 2],
        ["José Cuervo", "Licores y Vinos", "gramos", 680, 2],
        ["Jarana", "Licores y Vinos", "gramos", 450, 2],
        ["Reposado", "Licores y Vinos", "gramos", 680, 2],
        ["Vodkalla", "Licores y Vinos", "gramos", 450, 2],
        ["Triple sec", "Licores y Vinos", "gramos", 450, 2],
        ["Vino tinto Tavernello", "Licores y Vinos", "gramos", 680, 2],
        ["Undurraga", "Licores y Vinos", "gramos", 680, 2],
        ["Viña Esmeralda", "Licores y Vinos", "gramos", 680, 2],
        ["Aliwen", "Licores y Vinos", "gramos", 680, 2],
        ["Luis Felipe", "Licores y Vinos", "gramos", 680, 2],
        ["Espumoso rosé", "Licores y Vinos", "gramos", 680, 2],
        ["Aperol", "Licores y Vinos", "gramos", 680, 2],
        ["Granadine", "Licores y Vinos", "gramos", 450, 2],
    ])

    rows.extend([
        ["Jugo de guayaba", "Jugos naturales", "galones", 1.0, 3],
        ["Jugo de naranja", "Jugos naturales", "galones", 1.0, 3],
        ["Jugo de limón", "Jugos naturales", "galones", 0.5, 3],
        ["Limonada clásica", "Jugos naturales", "galones", 1.0, 3],
        ["Limonada de fresa", "Jugos naturales", "galones", 1.0, 3],
        ["Té de limón", "Jugos naturales", "galones", 1.0, 3],
        ["Jamaica", "Jugos naturales", "galones", 1.0, 3],
        ["Toronja", "Jugos naturales", "galones", 0.5, 3],
        ["Concentrado de limón", "Jugos naturales", "galones", 0.5, 3],
        ["Concentrado de mango", "Jugos naturales", "galones", 0.5, 3],
        ["Concentrado de guayaba", "Jugos naturales", "galones", 0.5, 3],
    ])

    rows.extend([
        ["Flan", "Postres", "porciones", 5, 4],
        ["Red velvet", "Postres", "porciones", 3, 4],
        ["Torta alemana", "Postres", "porciones", 3, 4],
        ["Pastel de zanahoria", "Postres", "porciones", 5, 4],
        ["Cheesecake de limón", "Postres", "porciones", 3, 4],
        ["Tres leches", "Postres", "porciones", 3, 4],
    ])

    return rows


def _build_inventario_values() -> tuple[list[list[object]], int]:
    dates = _date_headers()
    fixed = ["Producto", "Categoria", "Unidad", "Stock Min", "Proveedor ID"]
    header = fixed + dates
    responsable = ["Responsable", "", "", "", ""] + ["" for _ in dates]

    rows = _build_catalog_rows()
    trailing = ["" for _ in dates]
    body = [r + trailing[:] for r in rows]

    return [header, responsable] + body, len(dates)


def _format_inventario(sheet_id: int, values: list[list[object]]) -> None:
    header_dark = _hex_to_rgb("#1B5E63")
    header_light = _hex_to_rgb("#2E7D82")
    white = _hex_to_rgb("#FFFFFF")
    resp_yellow = _hex_to_rgb("#FFF9C4")
    resp_text = _hex_to_rgb("#5D4037")

    category_colors = {
        "Gaseosas y refrescos": _hex_to_rgb("#E3F2FD"),
        "Cervezas": _hex_to_rgb("#FFF3E0"),
        "Hard Seltzer": _hex_to_rgb("#F3E5F5"),
        "Licores y Vinos": _hex_to_rgb("#FCE4EC"),
        "Jugos naturales": _hex_to_rgb("#E8F5E9"),
        "Postres": _hex_to_rgb("#FFF8E1"),
    }

    total_rows = len(values)
    total_cols = len(values[0])

    reqs = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 5},
                },
                "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_dark,
                        "textFormat": {
                            "foregroundColor": white,
                            "bold": True,
                            "fontSize": 10,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 5,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": header_light}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": resp_yellow,
                        "textFormat": {
                            "foregroundColor": resp_text,
                            "bold": True,
                            "italic": True,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
    ]

    for row_idx in range(2, total_rows):
        categoria = values[row_idx][1]
        color = category_colors.get(categoria)
        if not color:
            continue
        reqs.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": total_cols,
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": color}},
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        )

    col_widths = [150, 150, 80, 80, 90]
    for idx, px in enumerate(col_widths):
        reqs.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": idx,
                        "endIndex": idx + 1,
                    },
                    "properties": {"pixelSize": px},
                    "fields": "pixelSize",
                }
            }
        )

    reqs.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,
                    "endIndex": total_cols,
                },
                "properties": {"pixelSize": 65},
                "fields": "pixelSize",
            }
        }
    )

    _batch_update(reqs)


def _catalogo_licores_rows() -> list[list[object]]:
    return [
        ["Producto", "Capacidad_ml", "Capacidad_oz", "Peso_lleno_g", "Peso_vacio_g", "ABV_pct", "Gramos_por_oz", "Notas"],
        ["Flor de Caña 12", 750, 25.4, "(PESAR HOY)", 680, 40, 27.5, "Botella vidrio oscuro"],
        ["Flor de Caña 18", 750, 25.4, "(PESAR HOY)", 690, 40, 27.5, ""],
        ["Flor de Caña Gran Reserva", 750, 25.4, "(PESAR HOY)", 700, 40, 27.5, ""],
        ["Extra Lite litro", 1000, 33.8, "(PESAR HOY)", 820, 35, 27.0, "Botella 1L"],
        ["Extra Lite 1/2", 375, 12.7, "(PESAR HOY)", 420, 35, 27.0, ""],
        ["José Cuervo", 750, 25.4, "(PESAR HOY)", 660, 38, 27.3, ""],
        ["Jarana", 375, 12.7, "(PESAR HOY)", 410, 38, 27.3, ""],
        ["Reposado", 750, 25.4, "(PESAR HOY)", 660, 38, 27.3, ""],
        ["Vodkalla", 375, 12.7, "(PESAR HOY)", 400, 38, 27.3, ""],
        ["Triple sec", 375, 12.7, "(PESAR HOY)", 410, 30, 26.5, ""],
        ["Vino tinto Tavernello", 750, 25.4, "(PESAR HOY)", 680, 13, 26.0, "Vino"],
        ["Undurraga", 750, 25.4, "(PESAR HOY)", 670, 13, 26.0, ""],
        ["Viña Esmeralda", 750, 25.4, "(PESAR HOY)", 670, 12, 26.0, ""],
        ["Aliwen", 750, 25.4, "(PESAR HOY)", 670, 13, 26.0, ""],
        ["Luis Felipe", 750, 25.4, "(PESAR HOY)", 670, 13, 26.0, ""],
        ["Espumoso rosé", 750, 25.4, "(PESAR HOY)", 660, 11, 25.8, ""],
        ["Aperol", 700, 23.7, "(PESAR HOY)", 620, 11, 25.8, ""],
        ["Granadine", 375, 12.7, "(PESAR HOY)", 400, 0, 25.5, "Sin alcohol"],
        ["* Pesar todas las botellas llenas HOY y reemplazar (PESAR HOY)", "", "", "", "", "", "", ""],
    ]


def _format_catalogo(sheet_id: int, row_count: int) -> None:
    dark_teal = _hex_to_rgb("#1B5E63")
    white = _hex_to_rgb("#FFFFFF")
    orange = _hex_to_rgb("#FFF3E0")

    reqs = [
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
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
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count - 1,
                    "startColumnIndex": 3,
                    "endColumnIndex": 4,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": orange}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        },
    ]

    widths = [220, 110, 110, 120, 110, 80, 120, 250]
    for idx, px in enumerate(widths):
        reqs.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": idx,
                        "endIndex": idx + 1,
                    },
                    "properties": {"pixelSize": px},
                    "fields": "pixelSize",
                }
            }
        )

    _batch_update(reqs)


def _update_recetas_bebidas() -> None:
    target_ingredientes = {
        "limonada clásica",
        "limonada de fresa",
        "jamaica",
        "té de limón",
        "jugo de guayaba",
        "jugo de naranja",
        "toronja",
    }
    note = "16oz vaso - 35% hielo = 10oz líquido neto"

    rows = _values_get(f"{SHEET_RECETAS}!A:D")
    if not rows:
        return

    changed = False
    for i in range(1, len(rows)):
        row = rows[i]
        while len(row) < 4:
            row.append("")
        ingrediente = str(row[1]).strip().lower() if len(row) > 1 else ""
        unidad = str(row[3]).strip().lower() if len(row) > 3 else ""
        if ingrediente in target_ingredientes and unidad == "oz":
            row[2] = "10"
            row[3] = "oz"
            changed = True

    notes_rows = _values_get(f"{SHEET_RECETAS}!A:E")
    if notes_rows:
        while len(notes_rows) < len(rows):
            notes_rows.append([""])
        for i in range(1, len(notes_rows)):
            row = notes_rows[i]
            while len(row) < 5:
                row.append("")
            ingrediente = str(row[1]).strip().lower()
            unidad = str(row[3]).strip().lower()
            if ingrediente in target_ingredientes and unidad == "oz":
                row[2] = "10"
                row[4] = note
                changed = True
        if changed:
            _values_put(f"{SHEET_RECETAS}!A1:E{len(notes_rows)}", notes_rows)


def _run_postgres_updates() -> None:
    db_url = DATABASE_URL if DATABASE_URL else DATABASE_URL_FALLBACK
    if "brunobot_bruno" in db_url:
        db_url = DATABASE_URL_FALLBACK
    if not db_url:
        raise RuntimeError("DATABASE_URL no esta configurado")

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE inventario_catalogo SET unidad_tipo = 'gramos' WHERE categoria = 'Licores y Vinos';")
            cur.execute(
                """
                UPDATE inventario_catalogo
                SET stock_minimo = 700
                WHERE categoria = 'Licores y Vinos'
                  AND unidad_tipo = 'gramos'
                  AND producto NOT LIKE '%litro%'
                  AND producto NOT LIKE '%1/2%';
                """
            )
            cur.execute("DELETE FROM inventario_diario WHERE fecha < CURRENT_DATE;")
        conn.commit()


def main() -> None:
    if not SPREADSHEET_ID:
        raise RuntimeError("GOOGLE_SHEETS_ID no definido")

    meta = _sheet_get()
    inventario_sheet_id = _sheet_id_from_meta(meta, SHEET_INVENTARIO)

    _values_clear(f"{SHEET_INVENTARIO}!A:ZZZ")

    inventario_values, date_cols = _build_inventario_values()
    _values_put(f"{SHEET_INVENTARIO}!A1", inventario_values)
    _format_inventario(inventario_sheet_id, inventario_values)

    catalogo_sheet_id = _ensure_sheet(SHEET_CATALOGO)
    _values_clear(f"{SHEET_CATALOGO}!A:ZZZ")
    cat_rows = _catalogo_licores_rows()
    _values_put(f"{SHEET_CATALOGO}!A1", cat_rows)
    _format_catalogo(catalogo_sheet_id, len(cat_rows))

    _update_recetas_bebidas()
    _run_postgres_updates()

    print("[OK] Sheet reconstruido")
    print("[OK] CATALOGO_LICORES creado con 18 productos")
    print(f"[OK] Fechas generadas: 27/04/2026 -> 31/12/2026 ({date_cols} columnas)")
    print("[OK] Postgres actualizado")
    print("[URL] https://docs.google.com/spreadsheets/d/1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw")


if __name__ == "__main__":
    main()
