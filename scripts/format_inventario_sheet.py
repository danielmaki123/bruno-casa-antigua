import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
REQUIRED_SHEETS = ["INVENTARIO_BEBIDAS", "PROVEEDORES", "POSTRES"]

_session = requests.Session()
_session.trust_env = False


def _hex_to_rgb(hex_color: str) -> dict:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Color HEX inválido: {hex_color}")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return {"red": r, "green": g, "blue": b}


def _find_token_path() -> Path:
    env_val = os.getenv("SHEETS_TOKEN_PATH", "").strip()
    candidates = [
        Path(env_val) if env_val else None,
        Path("/app/token.json"),
        ROOT / "token.json",
        Path.cwd() / "token.json",
    ]
    for c in candidates:
        if c and c.exists():
            return c
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

    new = resp.json()
    if "access_token" not in new:
        raise RuntimeError("Google token refresh no devolvió access_token")

    data["token"] = new["access_token"]
    data["expiry"] = (
        datetime.now(timezone.utc) + timedelta(seconds=int(new.get("expires_in", 3600)))
    ).isoformat().replace("+00:00", "Z")
    token_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return new["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _spreadsheet_id() -> str:
    sid = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    if not sid:
        raise RuntimeError("GOOGLE_SHEETS_ID no está configurado en .env")
    return sid


def _get_metadata(spreadsheet_id: str) -> dict:
    resp = _session.get(f"{BASE_URL}/{spreadsheet_id}", headers=_headers(), timeout=25)
    resp.raise_for_status()
    return resp.json()


def _get_values(spreadsheet_id: str, range_a1: str) -> list[list[str]]:
    resp = _session.get(
        f"{BASE_URL}/{spreadsheet_id}/values/{range_a1}",
        headers=_headers(),
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("values", [])


def _batch_update(spreadsheet_id: str, requests_payload: list[dict]) -> None:
    if not requests_payload:
        return
    resp = _session.post(
        f"{BASE_URL}/{spreadsheet_id}:batchUpdate",
        headers=_headers(),
        json={"requests": requests_payload},
        timeout=30,
    )
    resp.raise_for_status()


def _print_tab_audit(sheet_names: list[str]) -> None:
    required_set = set(REQUIRED_SHEETS)
    baseline_keep = {"INVENTARIO"}
    allowed = required_set | baseline_keep
    extras = sorted([name for name in sheet_names if name not in allowed])

    print("=== Auditoría de pestañas ===")
    print(f"Necesarias: {', '.join(REQUIRED_SHEETS)}")
    print(f"También conservar: {', '.join(sorted(baseline_keep))}")
    print("\nExistentes:")
    for n in sorted(sheet_names):
        print(f"- {n}")

    print("\nEstado requeridas:")
    for n in REQUIRED_SHEETS:
        print(f"- {n}: {'OK' if n in sheet_names else 'FALTA'}")

    print("\nExtras/No usadas:")
    if extras:
        for n in extras:
            print(f"- {n}")
    else:
        print("- Ninguna")


def _style_inventory(spreadsheet_id: str, sheet_id: int, rows: int, cols: int, values: list[list[str]]) -> None:
    dark_teal = _hex_to_rgb("#1B5E63")
    white = _hex_to_rgb("#FFFFFF")
    light_gray = _hex_to_rgb("#F5F5F5")
    light_blue = _hex_to_rgb("#E8F4FD")

    max_rows = max(rows, len(values), 2)
    max_cols = max(cols, max((len(r) for r in values), default=6), 6)

    requests_payload = []

    requests_payload.append(
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 5},
                },
                "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
            }
        }
    )

    requests_payload.append(
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"fontFamily": "Arial", "fontSize": 10}
                    }
                },
                "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
            }
        }
    )

    requests_payload.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": dark_teal,
                        "textFormat": {
                            "foregroundColor": white,
                            "bold": True,
                            "fontSize": 11,
                            "fontFamily": "Arial",
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        }
    )

    requests_payload.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": max_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": 5,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": light_gray}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
    )

    for c in range(5, max_cols):
        if (c - 5) % 2 == 1:
            requests_payload.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": max_rows,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1,
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": light_blue}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

    category_border_colors = {
        "Gaseosas": "#90CAF9",
        "Cervezas": "#FFCC80",
        "Hard Seltzer": "#CE93D8",
        "Licores": "#8E2430",
        "Jugos": "#81C784",
        "Postres": "#F48FB1",
    }

    for idx, row in enumerate(values[1:], start=1):
        category = row[1].strip() if len(row) > 1 and row[1] else ""
        color_hex = None
        for key, candidate in category_border_colors.items():
            if key == "Licores":
                if "licores" in category.lower():
                    color_hex = candidate
                    break
            elif category == key:
                color_hex = candidate
                break
        if color_hex:
            requests_payload.append(
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": idx,
                            "endRowIndex": idx + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": max_cols,
                        },
                        "left": {
                            "style": "SOLID",
                            "width": 2,
                            "color": _hex_to_rgb(color_hex),
                        },
                    }
                }
            )

    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {"pixelSize": 200},
                "fields": "pixelSize",
            }
        }
    )
    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2,
                },
                "properties": {"pixelSize": 120},
                "fields": "pixelSize",
            }
        }
    )
    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,
                    "endIndex": 3,
                },
                "properties": {"pixelSize": 80},
                "fields": "pixelSize",
            }
        }
    )
    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 3,
                    "endIndex": 4,
                },
                "properties": {"pixelSize": 80},
                "fields": "pixelSize",
            }
        }
    )
    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 4,
                    "endIndex": 5,
                },
                "properties": {"pixelSize": 90},
                "fields": "pixelSize",
            }
        }
    )

    if max_cols > 5:
        requests_payload.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 5,
                        "endIndex": max_cols,
                    },
                    "properties": {"pixelSize": 70},
                    "fields": "pixelSize",
                }
            }
        )

    requests_payload.append(
        {
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": max_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": max_cols,
                },
                "top": {"style": "SOLID", "color": _hex_to_rgb("#D0D0D0")},
                "bottom": {"style": "SOLID", "color": _hex_to_rgb("#D0D0D0")},
                "left": {"style": "SOLID", "color": _hex_to_rgb("#D0D0D0")},
                "right": {"style": "SOLID", "color": _hex_to_rgb("#D0D0D0")},
                "innerHorizontal": {"style": "SOLID", "color": _hex_to_rgb("#E0E0E0")},
                "innerVertical": {"style": "SOLID", "color": _hex_to_rgb("#E0E0E0")},
            }
        }
    )

    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {"pixelSize": 30},
                "fields": "pixelSize",
            }
        }
    )

    requests_payload.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": max_rows,
                },
                "properties": {"pixelSize": 22},
                "fields": "pixelSize",
            }
        }
    )

    _batch_update(spreadsheet_id, requests_payload)


def _style_providers(spreadsheet_id: str, sheet_id: int, rows: int, cols: int) -> None:
    dark_teal = _hex_to_rgb("#1B5E63")
    white = _hex_to_rgb("#FFFFFF")
    light_gray = _hex_to_rgb("#F7F7F7")

    max_rows = max(rows, 2)
    max_cols = max(cols, 5)

    requests_payload = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
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
                        "backgroundColor": dark_teal,
                        "textFormat": {
                            "foregroundColor": white,
                            "bold": True,
                            "fontSize": 11,
                            "fontFamily": "Arial",
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
                "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
            }
        },
    ]

    for r in range(1, max_rows):
        if r % 2 == 1:
            requests_payload.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": r,
                            "endRowIndex": r + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": max_cols,
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": light_gray}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

    _batch_update(spreadsheet_id, requests_payload)


def _style_postres(spreadsheet_id: str, sheet_id: int, rows: int, cols: int) -> None:
    dark_teal = _hex_to_rgb("#1B5E63")
    white = _hex_to_rgb("#FFFFFF")
    light_pink = _hex_to_rgb("#FDECEF")
    indicator = _hex_to_rgb("#FFF7CC")

    max_rows = max(rows, 2)
    max_cols = max(cols, 2)

    requests_payload = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
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
                        "backgroundColor": dark_teal,
                        "textFormat": {
                            "foregroundColor": white,
                            "bold": True,
                            "fontSize": 11,
                            "fontFamily": "Arial",
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
                "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
            }
        },
    ]

    for r in range(1, max_rows):
        if r % 2 == 1:
            requests_payload.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": r,
                            "endRowIndex": r + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": max_cols,
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": light_pink}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

    requests_payload.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": max_rows,
                            "startColumnIndex": 1,
                            "endColumnIndex": 2,
                        }
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=NOT(ISBLANK(B2))"}],
                        },
                        "format": {"backgroundColor": indicator},
                    },
                },
                "index": 0,
            }
        }
    )

    _batch_update(spreadsheet_id, requests_payload)


def main() -> None:
    spreadsheet_id = _spreadsheet_id()
    metadata = _get_metadata(spreadsheet_id)
    sheets = metadata.get("sheets", [])

    title_to_props = {
        s.get("properties", {}).get("title", ""): s.get("properties", {}) for s in sheets
    }
    sheet_names = [name for name in title_to_props if name]
    _print_tab_audit(sheet_names)

    missing = [name for name in REQUIRED_SHEETS if name not in title_to_props]
    if missing:
        raise RuntimeError(f"Faltan pestañas requeridas para formatear: {', '.join(missing)}")

    inv_props = title_to_props["INVENTARIO_BEBIDAS"]
    prov_props = title_to_props["PROVEEDORES"]
    post_props = title_to_props["POSTRES"]

    inv_values = _get_values(spreadsheet_id, "INVENTARIO_BEBIDAS!A:ZZ")

    _style_inventory(
        spreadsheet_id,
        inv_props["sheetId"],
        int(inv_props.get("gridProperties", {}).get("rowCount", 1000)),
        int(inv_props.get("gridProperties", {}).get("columnCount", 26)),
        inv_values,
    )
    _style_providers(
        spreadsheet_id,
        prov_props["sheetId"],
        int(prov_props.get("gridProperties", {}).get("rowCount", 1000)),
        int(prov_props.get("gridProperties", {}).get("columnCount", 10)),
    )
    _style_postres(
        spreadsheet_id,
        post_props["sheetId"],
        int(post_props.get("gridProperties", {}).get("rowCount", 1000)),
        int(post_props.get("gridProperties", {}).get("columnCount", 10)),
    )

    print("[OK] Sheet formateado correctamente")


if __name__ == "__main__":
    main()
